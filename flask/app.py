"""
Flask API - Picareta
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import base64
import io
import os
import re
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

try:
    import cv2
except Exception:  # pragma: no cover - ambiente pode não ter opencv instalado
    cv2 = None

try:
    import easyocr
except Exception:  # pragma: no cover - ambiente pode não ter easyocr instalado
    easyocr = None

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover - ambiente pode não ter ultralytics instalado
    YOLO = None

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "test"))
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_BYTES = int(os.environ.get("MAX_IMAGE_BYTES", 12 * 1024 * 1024))
PLATE_REGEX = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")
TEMPLATE_OLD = "LLLDDDD"
TEMPLATE_MERCOSUL = "LLLDLDD"
LETTER_FROM_DIGIT = {
    "0": "O",
    "1": "I",
    "2": "Z",
    "4": "A",
    "5": "S",
    "6": "G",
    "7": "T",
    "8": "B",
}
DIGIT_FROM_LETTER = {
    "A": "4",
    "B": "8",
    "D": "0",
    "G": "6",
    "I": "1",
    "L": "1",
    "O": "0",
    "Q": "0",
    "S": "5",
    "T": "7",
    "Z": "2",
}

_ocr_reader = None
_ocr_error = None
_yolo_model = None
_yolo_error = None
_yolo_model_path = None


def list_test_images():
    if not os.path.isdir(TEST_DIR):
        return []
    files = []
    for name in os.listdir(TEST_DIR):
        ext = os.path.splitext(name.lower())[1]
        if ext in ALLOWED_EXT:
            files.append(name)
    return sorted(files)


def safe_test_path(filename: str) -> str:
    # evita ../../
    filename = os.path.basename(filename)
    full = os.path.abspath(os.path.join(TEST_DIR, filename))
    if not full.startswith(TEST_DIR + os.sep):
        raise ValueError("invalid path")
    return full


def _extract_base64_payload(raw: str) -> Tuple[str, Optional[str]]:
    value = (raw or "").strip()
    if not value:
        raise ValueError("base64 vazio")

    mime_type = None
    if value.startswith("data:"):
        header, sep, body = value.partition(",")
        if not sep:
            raise ValueError("data URL inválida")
        if ";base64" not in header:
            raise ValueError("data URL sem ;base64")
        mime_type = header[5:].split(";")[0] or None
        value = body

    # Alguns clients enviam com espaços/quebras de linha.
    value = re.sub(r"\s+", "", value)
    if not value:
        raise ValueError("base64 vazio")
    return value, mime_type


def _decode_base64_image(raw: str) -> Tuple[Image.Image, Dict]:
    payload, mime_type = _extract_base64_payload(raw)

    try:
        image_bytes = base64.b64decode(payload, validate=True)
    except Exception:
        raise ValueError("base64 inválido")

    if not image_bytes:
        raise ValueError("base64 sem conteúdo")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError(f"imagem excede limite de {MAX_IMAGE_BYTES} bytes")

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        raise ValueError("não foi possível abrir imagem a partir do base64")

    meta = {
        "source": "base64",
        "mime_type": mime_type,
        "bytes": len(image_bytes),
        "width": img.size[0],
        "height": img.size[1],
    }
    return img, meta


def normalize_text(raw: str) -> str:
    return "".join(ch for ch in raw.upper() if ch.isalnum())


def _coerce_template(token: str, template: str) -> Optional[Tuple[str, int]]:
    if len(token) != len(template):
        return None
    out = []
    substitutions = 0
    for ch, expected in zip(token, template):
        if expected == "L":
            if ch.isalpha():
                out.append(ch)
            elif ch in LETTER_FROM_DIGIT:
                out.append(LETTER_FROM_DIGIT[ch])
                substitutions += 1
            else:
                return None
        else:  # expected == "D"
            if ch.isdigit():
                out.append(ch)
            elif ch in DIGIT_FROM_LETTER:
                out.append(DIGIT_FROM_LETTER[ch])
                substitutions += 1
            else:
                return None
    plate = "".join(out)
    if not PLATE_REGEX.match(plate):
        return None
    return plate, substitutions


def extract_plate_candidates(text: str) -> List[Dict]:
    token = normalize_text(text)
    if len(token) < 7:
        return []

    template_rank = {TEMPLATE_MERCOSUL: 0, TEMPLATE_OLD: 1}
    best_by_plate: Dict[str, Dict] = {}
    for i in range(len(token) - 6):
        chunk = token[i:i + 7]
        old = _coerce_template(chunk, TEMPLATE_OLD)
        mercosul = _coerce_template(chunk, TEMPLATE_MERCOSUL)
        if old:
            plate, penalty = old
            prev = best_by_plate.get(plate)
            candidate = {"plate": plate, "penalty": penalty, "pattern": TEMPLATE_OLD}
            if prev is None or (penalty, template_rank[TEMPLATE_OLD]) < (prev["penalty"], template_rank[prev["pattern"]]):
                best_by_plate[plate] = candidate
        if mercosul:
            plate, penalty = mercosul
            prev = best_by_plate.get(plate)
            candidate = {"plate": plate, "penalty": penalty, "pattern": TEMPLATE_MERCOSUL}
            if prev is None or (penalty, template_rank[TEMPLATE_MERCOSUL]) < (prev["penalty"], template_rank[prev["pattern"]]):
                best_by_plate[plate] = candidate

    return sorted(best_by_plate.values(), key=lambda c: (c["penalty"], template_rank[c["pattern"]], c["plate"]))


def _bbox_from_easyocr(box: List[List[float]], offset: Tuple[int, int]) -> Optional[List[int]]:
    try:
        xs = [int(round(p[0] + offset[0])) for p in box]
        ys = [int(round(p[1] + offset[1])) for p in box]
        return [min(xs), min(ys), max(xs), max(ys)]
    except Exception:
        return None


def _clip_bbox(bbox: List[int], width: int, height: int) -> List[int]:
    x1, y1, x2, y2 = bbox
    x1 = max(0, min(width - 1, x1))
    y1 = max(0, min(height - 1, y1))
    x2 = max(0, min(width - 1, x2))
    y2 = max(0, min(height - 1, y2))
    return [x1, y1, x2, y2]


def get_ocr_reader():
    global _ocr_reader, _ocr_error
    if _ocr_reader is not None:
        return _ocr_reader, None
    if _ocr_error is not None:
        return None, _ocr_error
    if easyocr is None:
        _ocr_error = "easyocr não instalado. Rode: pip install -r flask/requirements.txt"
        return None, _ocr_error

    try:
        _ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        return _ocr_reader, None
    except Exception as err:
        _ocr_error = str(err)
        return None, _ocr_error


def _resolve_yolo_model_path() -> Optional[str]:
    candidates = []
    env_path = os.environ.get("PLATE_MODEL_PATH")
    if env_path:
        candidates.append(os.path.abspath(env_path))
        candidates.append(os.path.abspath(os.path.join(BASE_DIR, env_path)))

    candidates.extend([
        os.path.join(BASE_DIR, "models", "license_plate.pt"),
        os.path.join(BASE_DIR, "models", "license_plate_detector.pt"),
        os.path.join(BASE_DIR, "..", "models", "license_plate.pt"),
        os.path.join(BASE_DIR, "..", "models", "license_plate_detector.pt"),
    ])

    for path in candidates:
        if os.path.isfile(path):
            return os.path.abspath(path)
    return None


def get_yolo_model():
    global _yolo_model, _yolo_error, _yolo_model_path
    if _yolo_model is not None:
        return _yolo_model, _yolo_model_path, None
    if _yolo_error is not None:
        return None, _yolo_model_path, _yolo_error
    if YOLO is None:
        _yolo_error = "ultralytics não instalado"
        return None, None, _yolo_error

    model_path = _resolve_yolo_model_path()
    _yolo_model_path = model_path
    if not model_path:
        _yolo_error = (
            "modelo YOLO de placa não encontrado. "
            "Defina PLATE_MODEL_PATH com caminho para .pt"
        )
        return None, None, _yolo_error

    try:
        _yolo_model = YOLO(model_path)
        return _yolo_model, model_path, None
    except Exception as err:
        _yolo_error = str(err)
        return None, model_path, _yolo_error


def _preprocess_for_ocr(img_bgr: np.ndarray) -> np.ndarray:
    if cv2 is None:
        return img_bgr
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    thr = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 11
    )
    return cv2.cvtColor(thr, cv2.COLOR_GRAY2BGR)


def _ocr_scan(
    np_img_rgb: np.ndarray,
    source: str,
    offset: Tuple[int, int] = (0, 0),
    source_confidence: Optional[float] = None,
) -> List[Dict]:
    reader, err = get_ocr_reader()
    if err:
        return [{
            "plate": None,
            "confidence": 0.0,
            "bbox": None,
            "source": source,
            "error": err,
        }]

    detections = []
    # Tenta em RGB e em versão pré-processada para aumentar chance em placas sujas/anguladas.
    variants = [np_img_rgb]
    if cv2 is not None:
        variants.append(_preprocess_for_ocr(cv2.cvtColor(np_img_rgb, cv2.COLOR_RGB2BGR))[:, :, ::-1])

    for variant_index, variant in enumerate(variants):
        try:
            read = reader.readtext(variant, detail=1, paragraph=False)
        except Exception:
            continue

        for box, text, conf in read:
            matches = extract_plate_candidates(text)
            if not matches:
                continue
            bbox = _bbox_from_easyocr(box, offset)
            for match in matches:
                plate = match["plate"]
                penalty = int(match["penalty"])
                score = float(conf)
                if source.startswith("yolo"):
                    score += 0.10
                if source_confidence is not None:
                    score += float(source_confidence) * 0.10
                if variant_index == 1:
                    score += 0.03
                # Penaliza candidatos que exigiram muitas correções de OCR (ex.: O<->0).
                score -= penalty * 0.03
                detections.append({
                    "plate": plate,
                    "confidence": min(1.0, round(score, 4)),
                    "bbox": bbox,
                    "source": source,
                    "raw_text": text,
                    "ocr_confidence": round(float(conf), 4),
                    "normalization_penalty": penalty,
                    "pattern": match["pattern"],
                })
    return detections


def _fallback_regions(np_img_rgb: np.ndarray) -> List[Tuple[str, np.ndarray, Tuple[int, int]]]:
    h, w = np_img_rgb.shape[:2]
    regions = [("full", np_img_rgb, (0, 0))]
    regions.append(("bottom_half", np_img_rgb[h // 2:h, 0:w], (0, h // 2)))
    regions.append(("bottom_third", np_img_rgb[(h * 2) // 3:h, 0:w], (0, (h * 2) // 3)))
    center_x1, center_x2 = w // 4, (w * 3) // 4
    regions.append(("center_bottom", np_img_rgb[h // 2:h, center_x1:center_x2], (center_x1, h // 2)))
    return regions


def _dedupe_candidates(candidates: List[Dict], width: int, height: int) -> List[Dict]:
    by_plate = {}
    for item in candidates:
        plate = item.get("plate")
        if not plate:
            continue
        bbox = item.get("bbox")
        if bbox:
            item["bbox"] = _clip_bbox(bbox, width, height)
        prev = by_plate.get(plate)
        item_key = (item["confidence"], -item.get("normalization_penalty", 99))
        prev_key = (
            prev["confidence"],
            -prev.get("normalization_penalty", 99),
        ) if prev else None
        if prev is None or item_key > prev_key:
            by_plate[plate] = item

    deduped = sorted(
        by_plate.values(),
        key=lambda x: (x["confidence"], -x.get("normalization_penalty", 99)),
        reverse=True,
    )
    return deduped[:10]


def recognize_plate(img: Image.Image) -> dict:
    np_img_rgb = np.array(img.convert("RGB"))
    height, width = np_img_rgb.shape[:2]
    pipeline = []
    candidates = []

    yolo_model, yolo_model_path, yolo_err = get_yolo_model()
    if yolo_model is not None:
        try:
            yolo_result = yolo_model.predict(np_img_rgb, conf=0.20, verbose=False)
            pipeline.append("yolo_plate_crop")
            if yolo_result and len(yolo_result[0].boxes) > 0:
                boxes = yolo_result[0].boxes
                for index, box in enumerate(boxes):
                    x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                    pad = max(10, int(0.03 * max(width, height)))
                    x1 = max(0, x1 - pad)
                    y1 = max(0, y1 - pad)
                    x2 = min(width, x2 + pad)
                    y2 = min(height, y2 + pad)
                    if x2 <= x1 or y2 <= y1:
                        continue
                    crop = np_img_rgb[y1:y2, x1:x2]
                    conf = float(box.conf[0].item()) if box.conf is not None else None
                    candidates.extend(_ocr_scan(crop, source=f"yolo_box_{index}", offset=(x1, y1), source_confidence=conf))
        except Exception as err:
            pipeline.append(f"yolo_failed:{err}")
    else:
        pipeline.append("yolo_unavailable")

    if not candidates:
        pipeline.append("fallback_ocr_regions")
        for region_name, region_img, offset in _fallback_regions(np_img_rgb):
            candidates.extend(_ocr_scan(region_img, source=region_name, offset=offset))

    deduped = _dedupe_candidates(candidates, width, height)
    best = deduped[0] if deduped else None

    return {
        "plate": best["plate"] if best else None,
        "confidence": best["confidence"] if best else 0.0,
        "bbox": best["bbox"] if best else None,
        "candidates": deduped,
        "engine": {
            "ocr": "easyocr",
            "yolo_model": yolo_model_path,
            "yolo_error": yolo_err,
            "pipeline": pipeline,
        },
    }


@app.route("/", methods=["GET"])
def index():
    """Endpoint principal"""
    return jsonify({
        "message": "Picareta Flask API",
        "status": "ok",
        "version": "1.0.0"
    }), 200


@app.route("/test", methods=["GET"])
def test_local_image():
    """
    Testa com imagem local em data/test.

    - GET /test -> usa a primeira imagem encontrada
    - GET /test?img=arquivo.jpeg -> usa a imagem especificada
    - GET /test?list=1 -> lista imagens disponíveis
    """
    images = list_test_images()
    if request.args.get("list") in ("1", "true", "yes"):
        return jsonify({
            "test_dir": TEST_DIR,
            "count": len(images),
            "images": images
        }), 200

    if not images:
        return jsonify({
            "error": "no_test_images",
            "message": f"Nenhuma imagem em {TEST_DIR}",
            "hint": "Coloque .jpg/.jpeg/.png/.webp em data/test/"
        }), 404

    selected = request.args.get("img") or images[0]
    if selected not in images:
        return jsonify({
            "error": "image_not_found",
            "selected": selected,
            "available": images
        }), 404

    try:
        path = safe_test_path(selected)
        img = Image.open(path).convert("RGB")
        w, h = img.size
        result = recognize_plate(img)
    except Exception as e:
        return jsonify({
            "error": "processing_failed",
            "message": str(e)
        }), 500

    return jsonify({
        "input": {
            "file": selected,
            "path": path,
            "width": w,
            "height": h
        },
        "result": result
    }), 200


@app.route("/recognize-base64", methods=["POST"])
def recognize_base64_image():
    """
    Reconhece placa a partir de imagem em base64.

    Payload JSON:
    {
      "base64": "...",
      "filename": "opcional.jpg"
    }

    Campos aceitos para imagem: base64 | image_base64 | image
    Aceita base64 puro ou data URL (data:image/jpeg;base64,...)
    """
    data = request.get_json(silent=True) or {}
    return _handle_base64_recognition(
        data=data,
        image_fields=("base64", "image_base64", "image"),
        include_ok=False,
    )


@app.route("/api/v1/plate/recognize", methods=["POST"])
def recognize_plate_for_nuxt():
    """
    Endpoint versionado para consumo do Nuxt.

    Payload JSON:
    {
      "imageBase64": "...",
      "filename": "opcional.jpg",
      "requestId": "opcional"
    }

    Response:
    {
      "ok": true,
      "input": {...},
      "result": {...},
      "requestId": "opcional"
    }
    """
    data = request.get_json(silent=True) or {}
    return _handle_base64_recognition(
        data=data,
        image_fields=("imageBase64",),
        include_ok=True,
        include_request_id=True,
    )


def _handle_base64_recognition(
    data: Dict,
    image_fields: Tuple[str, ...],
    include_ok: bool = False,
    include_request_id: bool = False,
):
    base64_input = None
    for field in image_fields:
        if field in data and isinstance(data.get(field), str) and data.get(field).strip():
            base64_input = data.get(field)
            break

    filename = data.get("filename")
    request_id = data.get("requestId")

    if not isinstance(base64_input, str) or not base64_input.strip():
        field_hint = " | ".join(image_fields)
        payload = {
            "error": "base64_required",
            "message": f"Envie '{field_hint}' no body JSON.",
        }
        if include_ok:
            payload["ok"] = False
        return jsonify(payload), 400

    try:
        img, input_meta = _decode_base64_image(base64_input)
        result = recognize_plate(img)
    except ValueError as err:
        payload = {
            "error": "invalid_base64_image",
            "message": str(err),
        }
        if include_ok:
            payload["ok"] = False
        return jsonify(payload), 400
    except Exception as err:
        payload = {
            "error": "processing_failed",
            "message": str(err),
        }
        if include_ok:
            payload["ok"] = False
        return jsonify(payload), 500

    response_input = dict(input_meta)
    if isinstance(filename, str) and filename.strip():
        response_input["filename"] = filename.strip()

    payload: Dict = {
        "input": response_input,
        "result": result,
    }

    if include_ok:
        payload["ok"] = True

    if include_request_id and isinstance(request_id, str) and request_id.strip():
        payload["requestId"] = request_id.strip()

    return jsonify(payload), 200


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
