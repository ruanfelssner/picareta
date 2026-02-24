"""
Flask API - Picareta
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import base64
import io
import os
import re
from time import perf_counter
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

_ultralytics_import_error = None
try:
    from ultralytics import YOLO
except Exception as err:  # pragma: no cover - ambiente pode não ter ultralytics instalado
    YOLO = None
    _ultralytics_import_error = str(err)

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "test"))
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_BYTES = int(os.environ.get("MAX_IMAGE_BYTES", 12 * 1024 * 1024))
# Perfil padrao de producao (fixo em codigo, sem dependencia de env de tuning).
MAX_PROCESS_SIDE = 1280
OCR_STRONG_CONFIDENCE = 0.72
OCR_MAX_FALLBACK_REGIONS = 3
OCR_UPSCALE_MAX_SIDE = 840
OCR_PREPROCESS_MAX_PIXELS = 1_000_000
OCR_PRELOAD_MODELS = True
OCR_AMBIGUOUS_DELTA = 0.06
OCR_ZERO_PRIORITY_DELTA = 0.05
OCR_MAX_PROCESS_MS = 30_000
OCR_MAX_VARIANTS = 3
OCR_NO_YOLO_MAX_FALLBACK_REGIONS = 3
OCR_MIN_TEXT_CONFIDENCE = 0.14
OCR_YOLO_IMGSZ = 640
OCR_YOLO_MAX_DET = 3
OCR_RESCUE_MAX_VARIANTS = 4
OCR_RESCUE_MIN_TEXT_CONFIDENCE = 0.08
OCR_SUPPORT_HIT_BOOST = 0.02
OCR_SUPPORT_SOURCE_BOOST = 0.02
OCR_SUPPORT_HIT_BOOST_MAX = 0.08
OCR_SUPPORT_SOURCE_BOOST_MAX = 0.04
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
# Ambiguidade comum em placas (ex.: 0 <-> 7 em reflexo/sujeira/fonte).
DIGIT_AMBIGUITY = {
    "0": ("7",),
    "7": ("0",),
}

_ocr_reader = None
_ocr_error = None
_yolo_model = None
_yolo_error = None
_yolo_model_path = None


def _is_deadline_reached(deadline_at: Optional[float]) -> bool:
    return deadline_at is not None and perf_counter() >= deadline_at


def _source_score_boost(source: str) -> float:
    if source.startswith("yolo"):
        return 0.10
    boosts = {
        "center_bottom": 0.06,
        "bottom_third": 0.05,
        "bottom_half": 0.03,
        "center_mid": 0.01,
        "middle_band": -0.02,
        "full": -0.05,
        "rescue_bottom_half": 0.02,
        "rescue_full": -0.04,
    }
    return boosts.get(source, 0.0)


def _bbox_score_adjustment(bbox: Optional[List[int]]) -> float:
    if not bbox:
        return 0.0
    x1, y1, x2, y2 = bbox
    w = max(1, x2 - x1)
    h = max(1, y2 - y1)
    ratio = w / float(h)
    if 2.2 <= ratio <= 7.5:
        return 0.02
    if ratio < 1.4 or ratio > 10.0:
        return -0.03
    return 0.0


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


def _register_candidate(
    best_by_plate: Dict[str, Dict], candidate: Dict, template_rank: Dict[str, int]
) -> None:
    plate = candidate["plate"]
    prev = best_by_plate.get(plate)
    if prev is None or (
        candidate["penalty"],
        template_rank[candidate["pattern"]],
    ) < (
        prev["penalty"],
        template_rank[prev["pattern"]],
    ):
        best_by_plate[plate] = candidate


def _expand_digit_ambiguities(plate: str, pattern: str, base_penalty: int) -> List[Dict]:
    expanded: List[Dict] = []
    for index, expected in enumerate(pattern):
        if expected != "D":
            continue
        current = plate[index]
        alternatives = DIGIT_AMBIGUITY.get(current, ())
        for alt_digit in alternatives:
            if alt_digit == current:
                continue
            alt_plate = f"{plate[:index]}{alt_digit}{plate[index + 1:]}"
            if not PLATE_REGEX.match(alt_plate):
                continue
            expanded.append(
                {
                    "plate": alt_plate,
                    "penalty": base_penalty + 1,
                    "pattern": pattern,
                }
            )
    return expanded


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
            candidate = {"plate": plate, "penalty": penalty, "pattern": TEMPLATE_OLD}
            _register_candidate(best_by_plate, candidate, template_rank)
            for alternative in _expand_digit_ambiguities(plate, TEMPLATE_OLD, penalty):
                _register_candidate(best_by_plate, alternative, template_rank)
        if mercosul:
            plate, penalty = mercosul
            candidate = {"plate": plate, "penalty": penalty, "pattern": TEMPLATE_MERCOSUL}
            _register_candidate(best_by_plate, candidate, template_rank)
            for alternative in _expand_digit_ambiguities(plate, TEMPLATE_MERCOSUL, penalty):
                _register_candidate(best_by_plate, alternative, template_rank)

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


def _resize_for_processing(np_img_rgb: np.ndarray) -> Tuple[np.ndarray, float]:
    if MAX_PROCESS_SIDE <= 0:
        return np_img_rgb, 1.0

    h, w = np_img_rgb.shape[:2]
    longest = max(h, w)
    if longest <= MAX_PROCESS_SIDE:
        return np_img_rgb, 1.0

    scale = MAX_PROCESS_SIDE / float(longest)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))

    if cv2 is not None:
        resized = cv2.resize(np_img_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
    else:
        resized = np.array(
            Image.fromarray(np_img_rgb).resize((new_w, new_h), Image.Resampling.BILINEAR)
        )
    return resized, scale


def _rescale_bbox(bbox: Optional[List[int]], process_scale: float, width: int, height: int) -> Optional[List[int]]:
    if not bbox:
        return None
    if process_scale == 1.0:
        return _clip_bbox(bbox, width, height)

    inv = 1.0 / process_scale
    restored = [int(round(value * inv)) for value in bbox]
    return _clip_bbox(restored, width, height)


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
        if _ultralytics_import_error:
            _yolo_error = f"ultralytics indisponivel: {_ultralytics_import_error}"
        else:
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


def _upscale_for_ocr(np_img_rgb: np.ndarray, factor: float = 2.0) -> np.ndarray:
    if cv2 is None or factor <= 1.0:
        return np_img_rgb
    h, w = np_img_rgb.shape[:2]
    new_w = max(w + 1, int(round(w * factor)))
    new_h = max(h + 1, int(round(h * factor)))
    return cv2.resize(np_img_rgb, (new_w, new_h), interpolation=cv2.INTER_CUBIC)


def _ocr_scan(
    np_img_rgb: np.ndarray,
    source: str,
    offset: Tuple[int, int] = (0, 0),
    source_confidence: Optional[float] = None,
    deadline_at: Optional[float] = None,
    max_variants: Optional[int] = None,
    min_text_confidence: Optional[float] = None,
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
    # Tenta em variantes para aumentar chance em placas sujas/anguladas/pequenas.
    # Evita variantes pesadas em imagens grandes para reduzir latência.
    h, w = np_img_rgb.shape[:2]
    pixels = h * w
    variants = [(np_img_rgb, 0.0)]

    if cv2 is not None:
        should_preprocess = pixels <= OCR_PREPROCESS_MAX_PIXELS or source.startswith("yolo")
        should_upscale = max(h, w) <= OCR_UPSCALE_MAX_SIDE or source.startswith("yolo")

        if should_preprocess:
            preprocessed = _preprocess_for_ocr(cv2.cvtColor(np_img_rgb, cv2.COLOR_RGB2BGR))[:, :, ::-1]
            variants.append((preprocessed, 0.03))

        if should_upscale:
            upscale_factor = 1.8 if max(h, w) < 320 else 1.5
            upscaled = _upscale_for_ocr(np_img_rgb, factor=upscale_factor)
            variants.append((upscaled, 0.05))

            if should_preprocess and pixels <= (OCR_PREPROCESS_MAX_PIXELS // 2):
                upscaled_preprocessed = _preprocess_for_ocr(
                    cv2.cvtColor(upscaled, cv2.COLOR_RGB2BGR)
                )[:, :, ::-1]
                variants.append((upscaled_preprocessed, 0.07))

    variant_limit = OCR_MAX_VARIANTS if max_variants is None else int(max_variants)
    if variant_limit > 0:
        variants = variants[:variant_limit]

    min_conf = OCR_MIN_TEXT_CONFIDENCE if min_text_confidence is None else float(min_text_confidence)
    source_boost = _source_score_boost(source)

    for variant_index, (variant, variant_boost) in enumerate(variants):
        if _is_deadline_reached(deadline_at):
            break
        try:
            read = reader.readtext(
                variant,
                detail=1,
                paragraph=False,
                allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                decoder="greedy",
                beamWidth=1,
            )
        except Exception:
            continue

        for box, text, conf in read:
            if float(conf) < min_conf and not source.startswith("yolo"):
                continue
            matches = extract_plate_candidates(text)
            if not matches:
                continue
            bbox = _bbox_from_easyocr(box, offset)
            for match in matches:
                plate = match["plate"]
                penalty = int(match["penalty"])
                score = float(conf)
                score += source_boost
                if source_confidence is not None:
                    score += float(source_confidence) * 0.10
                score += float(variant_boost)
                if variant_index >= 2:
                    score += 0.01
                score += _bbox_score_adjustment(bbox)
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
        if _has_strong_candidate(detections):
            break
    return detections


def _fallback_regions(np_img_rgb: np.ndarray) -> List[Tuple[str, np.ndarray, Tuple[int, int]]]:
    h, w = np_img_rgb.shape[:2]
    regions = []
    center_x1, center_x2 = w // 4, (w * 3) // 4
    regions.append(("center_bottom", np_img_rgb[h // 2:h, center_x1:center_x2], (center_x1, h // 2)))
    regions.append(("bottom_third", np_img_rgb[(h * 2) // 3:h, 0:w], (0, (h * 2) // 3)))
    regions.append(("bottom_half", np_img_rgb[h // 2:h, 0:w], (0, h // 2)))
    regions.append(("middle_band", np_img_rgb[h // 3:(h * 2) // 3, 0:w], (0, h // 3)))
    regions.append(("center_mid", np_img_rgb[h // 3:h, center_x1:center_x2], (center_x1, h // 3)))
    regions.append(("full", np_img_rgb, (0, 0)))
    return regions


def _dedupe_candidates(candidates: List[Dict], width: int, height: int) -> List[Dict]:
    by_plate: Dict[str, Dict] = {}
    for item in candidates:
        plate = item.get("plate")
        if not plate:
            continue
        bbox = item.get("bbox")
        if bbox:
            item["bbox"] = _clip_bbox(bbox, width, height)
        current = by_plate.get(plate)
        if current is None:
            by_plate[plate] = {
                "best": item,
                "hits": 1,
                "sources": {str(item.get("source") or "")},
            }
            continue

        current["hits"] += 1
        current["sources"].add(str(item.get("source") or ""))
        best_item = current["best"]
        item_key = (item["confidence"], -item.get("normalization_penalty", 99))
        best_key = (best_item["confidence"], -best_item.get("normalization_penalty", 99))
        if item_key > best_key:
            current["best"] = item

    deduped: List[Dict] = []
    for info in by_plate.values():
        best_item = dict(info["best"])
        hits = int(info["hits"])
        source_count = len(info["sources"])
        hit_boost = min(OCR_SUPPORT_HIT_BOOST_MAX, max(0, hits - 1) * OCR_SUPPORT_HIT_BOOST)
        source_boost = min(
            OCR_SUPPORT_SOURCE_BOOST_MAX,
            max(0, source_count - 1) * OCR_SUPPORT_SOURCE_BOOST,
        )
        support_boost = hit_boost + source_boost
        best_item["support_hits"] = hits
        best_item["support_sources"] = source_count
        best_item["support_boost"] = round(support_boost, 4)
        best_item["confidence"] = min(1.0, round(float(best_item["confidence"]) + support_boost, 4))
        deduped.append(best_item)

    deduped.sort(
        key=lambda x: (x["confidence"], -x.get("normalization_penalty", 99)),
        reverse=True,
    )
    return deduped[:10]


def _has_strong_candidate(candidates: List[Dict]) -> bool:
    if not candidates:
        return False
    best = max(
        candidates,
        key=lambda item: (
            float(item.get("confidence", 0.0)),
            -int(item.get("normalization_penalty", 99)),
        ),
    )
    return (
        float(best.get("confidence", 0.0)) >= OCR_STRONG_CONFIDENCE
        and int(best.get("normalization_penalty", 99)) <= 1
    )


def _is_ambiguous_top_pair(candidates: List[Dict]) -> bool:
    if len(candidates) < 2:
        return False

    first = candidates[0]
    second = candidates[1]

    first_plate = str(first.get("plate") or "")
    second_plate = str(second.get("plate") or "")
    if len(first_plate) != 7 or len(second_plate) != 7:
        return False
    if first_plate[:6] != second_plate[:6]:
        return False

    first_conf = float(first.get("confidence", 0.0))
    second_conf = float(second.get("confidence", 0.0))
    return abs(first_conf - second_conf) <= OCR_AMBIGUOUS_DELTA


def _prioritize_zero_last_digit(candidates: List[Dict]) -> Tuple[List[Dict], bool]:
    if len(candidates) < 2:
        return candidates, False

    ordered = list(candidates)
    for idx, item in enumerate(ordered):
        plate = str(item.get("plate") or "")
        if len(plate) != 7 or not plate.endswith("7"):
            continue

        paired_plate = f"{plate[:6]}0"
        zero_idx = next(
            (index for index, candidate in enumerate(ordered) if str(candidate.get("plate") or "") == paired_plate),
            None,
        )
        if zero_idx is None or zero_idx < idx:
            continue

        seven_conf = float(item.get("confidence", 0.0))
        zero_candidate = ordered[zero_idx]
        zero_conf = float(zero_candidate.get("confidence", 0.0))
        if (seven_conf - zero_conf) > OCR_ZERO_PRIORITY_DELTA:
            continue

        seven_penalty = int(item.get("normalization_penalty", 99))
        zero_penalty = int(zero_candidate.get("normalization_penalty", 99))
        if (zero_penalty - seven_penalty) > 1:
            continue

        chosen = ordered.pop(zero_idx)
        ordered.insert(idx, chosen)
        return ordered, True

    return ordered, False


def recognize_plate(img: Image.Image) -> dict:
    started = perf_counter()
    deadline_at = (started + (OCR_MAX_PROCESS_MS / 1000.0)) if OCR_MAX_PROCESS_MS > 0 else None
    timeout_reached = False
    np_img_original = np.array(img.convert("RGB"))
    height, width = np_img_original.shape[:2]
    np_img_rgb, process_scale = _resize_for_processing(np_img_original)
    proc_height, proc_width = np_img_rgb.shape[:2]

    pipeline = []
    candidates = []
    timings = {}

    yolo_model, yolo_model_path, yolo_err = get_yolo_model()
    if yolo_model is not None and not _is_deadline_reached(deadline_at):
        yolo_started = perf_counter()
        try:
            yolo_result = yolo_model.predict(
                np_img_rgb,
                conf=0.12,
                imgsz=OCR_YOLO_IMGSZ,
                max_det=OCR_YOLO_MAX_DET,
                verbose=False,
            )
            pipeline.append("yolo_plate_crop")
            if yolo_result and len(yolo_result[0].boxes) > 0:
                boxes = yolo_result[0].boxes
                for index, box in enumerate(boxes):
                    if _is_deadline_reached(deadline_at):
                        timeout_reached = True
                        pipeline.append("deadline_reached:yolo_boxes")
                        break
                    x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                    pad = max(8, int(0.03 * max(proc_width, proc_height)))
                    x1 = max(0, x1 - pad)
                    y1 = max(0, y1 - pad)
                    x2 = min(proc_width, x2 + pad)
                    y2 = min(proc_height, y2 + pad)
                    if x2 <= x1 or y2 <= y1:
                        continue
                    crop = np_img_rgb[y1:y2, x1:x2]
                    conf = float(box.conf[0].item()) if box.conf is not None else None
                    crop_candidates = _ocr_scan(
                        crop,
                        source=f"yolo_box_{index}",
                        offset=(x1, y1),
                        source_confidence=conf,
                        deadline_at=deadline_at,
                    )
                    candidates.extend(crop_candidates)

                    if _has_strong_candidate(crop_candidates):
                        pipeline.append(f"yolo_short_circuit:yolo_box_{index}")
                        break
        except Exception as err:
            pipeline.append(f"yolo_failed:{err}")
        finally:
            timings["yolo_ms"] = int(round((perf_counter() - yolo_started) * 1000))
    else:
        pipeline.append("yolo_unavailable")

    if not candidates and not _is_deadline_reached(deadline_at):
        fallback_started = perf_counter()
        pipeline.append("fallback_ocr_regions")
        regions = _fallback_regions(np_img_rgb)
        if OCR_MAX_FALLBACK_REGIONS > 0:
            regions = regions[:OCR_MAX_FALLBACK_REGIONS]
        if yolo_model is None and OCR_NO_YOLO_MAX_FALLBACK_REGIONS > 0:
            regions = regions[:OCR_NO_YOLO_MAX_FALLBACK_REGIONS]

        for region_name, region_img, offset in regions:
            if _is_deadline_reached(deadline_at):
                timeout_reached = True
                pipeline.append("deadline_reached:fallback_regions")
                break
            region_candidates = _ocr_scan(
                region_img,
                source=region_name,
                offset=offset,
                deadline_at=deadline_at,
            )
            candidates.extend(region_candidates)
            if _has_strong_candidate(region_candidates):
                pipeline.append(f"fallback_short_circuit:{region_name}")
                break

        timings["fallback_ms"] = int(round((perf_counter() - fallback_started) * 1000))

        # Se YOLO estiver indisponivel e o fallback padrao falhar, roda um passe de resgate
        # mais tolerante antes de desistir.
        if not candidates and yolo_model is None and not _is_deadline_reached(deadline_at):
            rescue_started = perf_counter()
            pipeline.append("fallback_rescue_no_yolo")
            rescue_regions = [
                ("rescue_bottom_half", np_img_rgb[proc_height // 2:proc_height, 0:proc_width], (0, proc_height // 2)),
                ("rescue_full", np_img_rgb, (0, 0)),
            ]
            for region_name, region_img, offset in rescue_regions:
                if _is_deadline_reached(deadline_at):
                    timeout_reached = True
                    pipeline.append("deadline_reached:rescue_regions")
                    break
                rescue_candidates = _ocr_scan(
                    region_img,
                    source=region_name,
                    offset=offset,
                    deadline_at=deadline_at,
                    max_variants=OCR_RESCUE_MAX_VARIANTS,
                    min_text_confidence=OCR_RESCUE_MIN_TEXT_CONFIDENCE,
                )
                candidates.extend(rescue_candidates)
                if _has_strong_candidate(rescue_candidates):
                    pipeline.append(f"rescue_short_circuit:{region_name}")
                    break
            timings["fallback_rescue_ms"] = int(round((perf_counter() - rescue_started) * 1000))
    elif not candidates and _is_deadline_reached(deadline_at):
        timeout_reached = True
        pipeline.append("deadline_reached:before_fallback")

    if _is_deadline_reached(deadline_at):
        timeout_reached = True

    deduped = _dedupe_candidates(candidates, proc_width, proc_height)
    deduped, zero_priority_applied = _prioritize_zero_last_digit(deduped)
    if zero_priority_applied:
        pipeline.append("prioritize_zero_last_digit")
    if process_scale != 1.0:
        for candidate in deduped:
            candidate["bbox"] = _rescale_bbox(candidate.get("bbox"), process_scale, width, height)
    ambiguous_top_pair = _is_ambiguous_top_pair(deduped)
    best = None if ambiguous_top_pair else (deduped[0] if deduped else None)
    if ambiguous_top_pair:
        pipeline.append("ambiguous_top_pair")

    timings["total_ms"] = int(round((perf_counter() - started) * 1000))
    timings["max_process_ms"] = OCR_MAX_PROCESS_MS
    timings["timeout_reached"] = 1 if timeout_reached else 0

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
            "timings_ms": timings,
            "ambiguous_top_pair": ambiguous_top_pair,
            "zero_priority_applied": zero_priority_applied,
            "image_scale": round(process_scale, 4),
            "input_size": {"width": width, "height": height},
            "process_size": {"width": proc_width, "height": proc_height},
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


def _maybe_preload_models():
    if not OCR_PRELOAD_MODELS:
        return
    get_yolo_model()
    get_ocr_reader()


_maybe_preload_models()


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
