"""
Flask API - Picareta
"""
from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS
import base64
import io
import json
import os
import re
from queue import Queue, Empty
from threading import Thread
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

try:
    from utils.ocr_corrections import normalize_plate_aggressive
except Exception:  # pragma: no cover
    normalize_plate_aggressive = None

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
OCR_ZERO_PRIORITY_PENULTIMATE_NINE_NO_YOLO_DELTA = 0.12
OCR_PREFIX_AMBIGUOUS_DELTA = 0.08
OCR_PREFIX_Y_OVER_V_PRIORITY_DELTA = 0.02
OCR_PENULTIMATE_2_PRIORITY_DELTA = 0.08
OCR_FOURTH_7_PRIORITY_DELTA = 0.03
OCR_PENULTIMATE_2_AMBIGUOUS_DELTA = 0.10
OCR_MIDDLE_O_D_PRIORITY_DELTA = 0.35
OCR_MIDDLE_O_D_AMBIGUOUS_DELTA = 0.20
OCR_MIDDLE_O_D_INJECT_CONF_BOOST = 0.018
OCR_MIDDLE_O_D_INJECT_PENALTY_DELTA = 0.12
OCR_LAST_7_TO_0_INJECT_CONF_BOOST = 0.026
OCR_LAST_7_TO_0_INJECT_PENALTY_DELTA = 0.10
OCR_LAST_7_TO_0_INJECT_MAX_CONFIDENCE = 0.90
OCR_LAST_7_TO_0_INJECT_MAX_RAW_OCR_CONFIDENCE = 0.58
OCR_FOURTH_1_4_PRIORITY_DELTA = 0.08
OCR_ENABLE_FOURTH_1_4_PRIORITY = False
OCR_PENULTIMATE_0_9_PRIORITY_DELTA = 0.02
OCR_PENULTIMATE_0_9_PRIORITY_MAX_PENALTY_GAP = 0.35
OCR_PENULTIMATE_0_9_PRIORITY_MIN_TEMPLATE_DIFF = -0.004
OCR_PENULTIMATE_0_9_LOW_PENALTY_CONF_GAP_MAX = 0.16
OCR_PENULTIMATE_0_9_LOW_PENALTY_GAP_MIN = 0.45
OCR_LOW_PENALTY_PRIORITY_CONF_GAP_MAX = 0.14
OCR_LOW_PENALTY_PRIORITY_PENALTY_GAP_MIN = 0.75
OCR_MAX_PROCESS_MS = 30_000
OCR_MAX_VARIANTS = 3
OCR_NO_YOLO_MAX_FALLBACK_REGIONS = 5
OCR_NO_YOLO_FALLBACK_MAX_MS = 11_000
OCR_NO_YOLO_FALLBACK_MAX_VARIANTS = 3
OCR_MIN_TEXT_CONFIDENCE = 0.14
OCR_CONTOUR_MAX_MS = 1700
OCR_CONTOUR_MAX_REGIONS = 3
OCR_CONTOUR_SCAN_MAX = 120
OCR_CONTOUR_OCR_MAX_VARIANTS = 2
OCR_CONTOUR_ROI_START_RATIO = 0.20
OCR_CONTOUR_ACCEPT_CONFIDENCE = 0.42
OCR_CONTOUR_ACCEPT_RAW_CONFIDENCE = 0.18
OCR_YOLO_IMGSZ = 640
OCR_YOLO_MAX_DET = 3
OCR_RESCUE_MAX_VARIANTS = 4
OCR_RESCUE_MIN_TEXT_CONFIDENCE = 0.04
OCR_NO_YOLO_RESCUE_MIN_REMAINING_MS = 4_500
OCR_NO_YOLO_LAST_CHANCE_MAX_MS = 9_000
OCR_LAST_CHANCE_MAX_VARIANTS = 2
OCR_LAST_CHANCE_MIN_TEXT_CONFIDENCE = 0.03
OCR_SUPPORT_HIT_BOOST = 0.02
OCR_SUPPORT_SOURCE_BOOST = 0.02
OCR_SUPPORT_HIT_BOOST_MAX = 0.08
OCR_SUPPORT_SOURCE_BOOST_MAX = 0.04
OCR_POSITION_BOOST_MAX = 0.06
OCR_LOW_CERTAINTY_CONFIDENCE = 0.72
OCR_MERCOSUL_MIDDLE_PRIORITY_DELTA = 0.05
OCR_TEMPLATE_RERANK_THRESHOLD = 0.88
OCR_TEMPLATE_RERANK_TOP_N = 80
OCR_TEMPLATE_RERANK_MIN_SCORE = 0.45
OCR_TEMPLATE_RERANK_BOOST_MAX = 0.22
OCR_TEMPLATE_CHAR_MATCH_WEIGHT = 0.55
OCR_CANDIDATE_POOL_LIMIT = 80
OCR_RESPONSE_CANDIDATES_LIMIT = 20
OCR_TEMPLATE_PATH = os.path.join(BASE_DIR, "models", "char_templates.json")
OCR_PLATE_ALLOWLIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
OCR_BEAMSEARCH_WIDTH = 5
OCR_BEAMSEARCH_MAX_VARIANTS = 2
OCR_BEAMSEARCH_MAX_PIXELS = 900_000
OCR_AGGRESSIVE_CORRECTION = True
OCR_AGGRESSIVE_EXTRA_PENALTY = 2.6
OCR_PATTERN_MERCOSUL_BOOST = 0.018
OCR_PATTERN_OLD_PENALTY = 0.012
OCR_LOW_CERTAINTY_SINGLE_HIT_CONFIDENCE = 0.84
OCR_LOW_CERTAINTY_YOLO_SINGLE_HIT_CONFIDENCE = 0.90
OCR_LOW_CERTAINTY_BEAM_CONFIDENCE = 0.85
OCR_LOW_CERTAINTY_AGGRESSIVE_CONFIDENCE = 0.90
OCR_LOW_CERTAINTY_SMALL_GAP = 0.045
OCR_LOW_CERTAINTY_RAW_OCR_CONFIDENCE = 0.52
OCR_LOW_CERTAINTY_TEMPLATE_SCORE = 0.60
OCR_YOLO_TEXTBOX_MIN_WIDTH_RATIO = 0.24
OCR_YOLO_TEXTBOX_MIN_HEIGHT_RATIO = 0.08
OCR_YOLO_TEXTBOX_MAX_HEIGHT_RATIO = 0.92
OCR_YOLO_TEXTBOX_MIN_AREA_RATIO = 0.02
OCR_TEXTBOX_MIN_ASPECT = 1.2
OCR_TEXTBOX_MIN_ASPECT_RELAXED = 0.82
OCR_TEXTBOX_MAX_ASPECT = 10.8
OCR_YOLO_BOX_MIN_ASPECT = 1.35
OCR_YOLO_BOX_MAX_ASPECT = 11.0
OCR_YOLO_BOX_MIN_AREA_RATIO = 0.0009
OCR_YOLO_BOX_MAX_AREA_RATIO = 0.20
OCR_YOLO_BOX_MIN_CENTER_Y = 0.12
OCR_YOLO_BOX_MAX_CENTER_Y = 0.96
OCR_YOLO_BOX_CENTER_X_MARGIN = 0.50
OCR_YOLO_OCR_TOKEN_MAX_LEN = 12
OCR_OLD_TO_MERCOSUL_CONVERSION_PENALTY = 0.18
OCR_NON_PLATE_KEYWORDS = ("BRASIL", "MERCOSUL")
PLATE_REGEX = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")
PLATE_REGEX_MERCOSUL = re.compile(r"^[A-Z]{3}[0-9][A-Z][0-9]{2}$")
PLATE_REGEX_OLD = re.compile(r"^[A-Z]{3}[0-9]{4}$")
TEMPLATE_OLD = "LLLDDDD"
TEMPLATE_MERCOSUL = "LLLDLDD"
OLD_DIGIT_TO_MERCOSUL_LETTER = {
    "0": "A",
    "1": "B",
    "2": "C",
    "3": "D",
    "4": "E",
    "5": "F",
    "6": "G",
    "7": "H",
    "8": "I",
    "9": "J",
}
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
    "1": ("7",),
    "2": ("7", "9"),
    "7": ("0", "1", "2"),
    "9": ("2",),
}
POSITIONAL_DIGIT_AMBIGUITY = {
    3: {"1": ("7", "4"), "4": ("1",), "7": ("1",)},
    5: {"0": ("9",), "2": ("7", "9"), "7": ("2",), "9": ("2", "0")},
    6: {"0": ("7",), "7": ("0",)},
}
DIGIT_CHANGE_COST = {
    ("0", "7"): 0.55,
    ("7", "0"): 0.55,
    ("1", "7"): 0.70,
    ("7", "1"): 0.72,
    ("1", "4"): 0.76,
    ("4", "1"): 0.78,
    ("0", "9"): 0.74,
    ("9", "0"): 0.74,
    ("2", "9"): 0.78,
    ("9", "2"): 0.78,
    ("2", "7"): 0.82,
    ("7", "2"): 0.82,
}
DIGIT_POSITION_COST_MULTIPLIER = {
    3: 0.92,
    5: 0.90,
    6: 0.85,
}
# Ambiguidade visual comum em letras (ex.: perspectiva/reflexo/fonte).
LETTER_AMBIGUITY = {
    "A": ("R",),
    "R": ("A", "K"),
    "T": ("Y", "I"),
    "Y": ("T", "V"),
    "U": ("O", "V"),
    "O": ("U", "Q", "D"),
    "D": ("O", "Q"),
    "V": ("Y", "U"),
    "M": ("N",),
    "N": ("M",),
    "K": ("R", "X"),
    "X": ("K",),
}
LETTER_CHANGE_COST = {
    ("A", "R"): 0.35,
    ("R", "A"): 0.45,
    ("T", "Y"): 0.30,
    ("Y", "T"): 0.35,
    ("U", "O"): 0.30,
    ("O", "U"): 0.45,
    ("U", "V"): 0.40,
    ("V", "Y"): 0.45,
    ("V", "U"): 0.42,
    ("Y", "V"): 0.34,
    ("D", "O"): 0.40,
    ("O", "D"): 0.55,
}

_ocr_reader = None
_ocr_error = None
_yolo_model = None
_yolo_error = None
_yolo_model_path = None
_char_templates = None
_char_templates_error = None
_char_templates_meta = {}


def _is_deadline_reached(deadline_at: Optional[float]) -> bool:
    return deadline_at is not None and perf_counter() >= deadline_at


def _remaining_deadline_ms(deadline_at: Optional[float]) -> float:
    if deadline_at is None:
        return float("inf")
    return max(0.0, (deadline_at - perf_counter()) * 1000.0)


def _min_deadline(deadline_a: Optional[float], deadline_b: Optional[float]) -> Optional[float]:
    if deadline_a is None:
        return deadline_b
    if deadline_b is None:
        return deadline_a
    return min(deadline_a, deadline_b)


def _source_score_boost(source: str) -> float:
    if source.startswith("yolo"):
        return 0.10
    boosts = {
        "center_bottom": 0.06,
        "bottom_third": 0.05,
        "bottom_half": 0.03,
        "center_mid": 0.01,
        "noyolo_top_center": 0.04,
        "noyolo_mid_center": 0.03,
        "noyolo_lower_band": 0.04,
        "contour_plate_0": 0.10,
        "contour_plate_1": 0.09,
        "contour_plate_2": 0.08,
        "contour_plate_3": 0.07,
        "contour_plate_4": 0.06,
        "contour_plate_5": 0.05,
        "last_top_half_center": 0.03,
        "last_mid_center": 0.02,
        "last_center_tall": 0.02,
        "last_bottom_half_center": 0.02,
        "last_top_half": -0.01,
        "middle_band": -0.02,
        "full": -0.05,
        "rescue_bottom_half": 0.02,
        "rescue_full": -0.04,
    }
    return boosts.get(source, 0.0)


def _pattern_score_adjustment(pattern: Optional[str]) -> float:
    if pattern == TEMPLATE_MERCOSUL:
        return OCR_PATTERN_MERCOSUL_BOOST
    if pattern == TEMPLATE_OLD:
        return -OCR_PATTERN_OLD_PENALTY
    return 0.0


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


def _position_score_adjustment(bbox: Optional[List[int]], width: int, height: int) -> float:
    if not bbox or width <= 0 or height <= 0:
        return 0.0
    x1, y1, x2, y2 = bbox
    cx = ((x1 + x2) / 2.0) / float(width)
    cy = ((y1 + y2) / 2.0) / float(height)

    score = 0.0
    # Placa traseira normalmente aparece na metade inferior da foto.
    if cy >= 0.60:
        score += 0.04
    elif cy < 0.45:
        score -= 0.04

    # Em geral fica proxima ao centro horizontal.
    if abs(cx - 0.5) <= 0.30:
        score += 0.01
    else:
        score -= 0.01

    if score > OCR_POSITION_BOOST_MAX:
        return OCR_POSITION_BOOST_MAX
    if score < -OCR_POSITION_BOOST_MAX:
        return -OCR_POSITION_BOOST_MAX
    return score


def _bbox_from_easyocr_local(box: List[List[float]]) -> Optional[List[int]]:
    try:
        xs = [int(round(p[0])) for p in box]
        ys = [int(round(p[1])) for p in box]
        return [min(xs), min(ys), max(xs), max(ys)]
    except Exception:
        return None


def _is_plausible_plate_text_box(
    local_bbox: Optional[List[int]],
    image_width: int,
    image_height: int,
    source: str,
) -> bool:
    if not local_bbox or image_width <= 0 or image_height <= 0:
        return True

    x1, y1, x2, y2 = local_bbox
    bw = max(1, x2 - x1)
    bh = max(1, y2 - y1)
    aspect = bw / float(bh)
    width_ratio = bw / float(image_width)
    height_ratio = bh / float(image_height)
    area_ratio = (bw * bh) / float(max(1, image_width * image_height))
    cx = ((x1 + x2) / 2.0) / float(image_width)
    cy = ((y1 + y2) / 2.0) / float(image_height)

    min_aspect = OCR_TEXTBOX_MIN_ASPECT
    if (
        source.startswith("noyolo_")
        or source.startswith("last_")
        or source.startswith("rescue_")
        or source in {"center_bottom", "bottom_half", "bottom_third", "center_mid"}
    ):
        min_aspect = OCR_TEXTBOX_MIN_ASPECT_RELAXED

    if aspect < min_aspect or aspect > OCR_TEXTBOX_MAX_ASPECT:
        return False

    if source.startswith("yolo_box_"):
        if width_ratio < OCR_YOLO_TEXTBOX_MIN_WIDTH_RATIO:
            return False
        if height_ratio < OCR_YOLO_TEXTBOX_MIN_HEIGHT_RATIO or height_ratio > OCR_YOLO_TEXTBOX_MAX_HEIGHT_RATIO:
            return False
        if area_ratio < OCR_YOLO_TEXTBOX_MIN_AREA_RATIO:
            return False
        if cx < 0.12 or cx > 0.88:
            return False
        if cy < 0.10 or cy > 0.90:
            return False

    return True


def _is_plausible_yolo_detection_box(
    bbox: List[int],
    image_width: int,
    image_height: int,
) -> bool:
    if not bbox or image_width <= 0 or image_height <= 0:
        return False

    x1, y1, x2, y2 = bbox
    bw = max(1, x2 - x1)
    bh = max(1, y2 - y1)
    aspect = bw / float(bh)
    area_ratio = (bw * bh) / float(max(1, image_width * image_height))
    cx = ((x1 + x2) / 2.0) / float(image_width)
    cy = ((y1 + y2) / 2.0) / float(image_height)

    if aspect < OCR_YOLO_BOX_MIN_ASPECT or aspect > OCR_YOLO_BOX_MAX_ASPECT:
        return False
    if area_ratio < OCR_YOLO_BOX_MIN_AREA_RATIO or area_ratio > OCR_YOLO_BOX_MAX_AREA_RATIO:
        return False
    if cy < OCR_YOLO_BOX_MIN_CENTER_Y or cy > OCR_YOLO_BOX_MAX_CENTER_Y:
        return False
    if abs(cx - 0.5) > OCR_YOLO_BOX_CENTER_X_MARGIN:
        return False
    return True


def _is_non_plate_short_token(token: str) -> bool:
    value = normalize_text(token)
    if not value:
        return False
    for keyword in OCR_NON_PLATE_KEYWORDS:
        if value == keyword:
            return True
        # Ex.: "SBRASIL" (detecção parcial do cabeçalho), sem conteúdo adicional de placa.
        if len(value) <= (len(keyword) + 1) and (keyword in value or value in keyword):
            return True
    return False


def _decode_template_png(value: str) -> Optional[np.ndarray]:
    if not value:
        return None
    try:
        raw = base64.b64decode(value, validate=True)
    except Exception:
        return None
    if not raw:
        return None
    if cv2 is not None:
        arr = np.frombuffer(raw, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    else:
        try:
            img = np.array(Image.open(io.BytesIO(raw)).convert("L"))
        except Exception:
            return None
    if img is None or img.size == 0:
        return None
    return (img > 127).astype(np.uint8)


def get_char_templates() -> Tuple[Optional[Dict[str, np.ndarray]], Optional[Dict], Optional[str]]:
    global _char_templates, _char_templates_error, _char_templates_meta
    if _char_templates is not None:
        return _char_templates, _char_templates_meta, None
    if _char_templates_error is not None:
        return None, None, _char_templates_error
    if not os.path.isfile(OCR_TEMPLATE_PATH):
        _char_templates_error = (
            "char templates indisponiveis. Gere com "
            "`python flask/scripts/build_char_templates_from_svg.py`"
        )
        return None, None, _char_templates_error
    try:
        with open(OCR_TEMPLATE_PATH, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        raw_templates = payload.get("templates") or {}
        loaded: Dict[str, np.ndarray] = {}
        for ch, encoded in raw_templates.items():
            if not isinstance(ch, str) or len(ch) != 1:
                continue
            if not isinstance(encoded, str):
                continue
            decoded = _decode_template_png(encoded)
            if decoded is None:
                continue
            loaded[ch.upper()] = decoded
        if not loaded:
            _char_templates_error = "arquivo de char templates sem dados validos"
            return None, None, _char_templates_error
        size = payload.get("template_size") or {}
        _char_templates_meta = {
            "path": OCR_TEMPLATE_PATH,
            "template_width": int(size.get("width") or 0),
            "template_height": int(size.get("height") or 0),
            "charset": str(payload.get("charset") or ""),
            "count": len(loaded),
        }
        _char_templates = loaded
        return _char_templates, _char_templates_meta, None
    except Exception as err:
        _char_templates_error = str(err)
        return None, None, _char_templates_error


def _resize_binary_keep_aspect(binary: np.ndarray, width: int, height: int) -> np.ndarray:
    if binary.size == 0:
        return np.zeros((height, width), dtype=np.uint8)
    h, w = binary.shape[:2]
    if h <= 0 or w <= 0:
        return np.zeros((height, width), dtype=np.uint8)
    scale = min(width / float(w), height / float(h))
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    if cv2 is not None:
        resized = cv2.resize(binary, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
    else:
        resized = np.array(
            Image.fromarray((binary * 255).astype(np.uint8)).resize(
                (new_w, new_h),
                Image.Resampling.NEAREST,
            )
        )
        resized = (resized > 127).astype(np.uint8)
    canvas = np.zeros((height, width), dtype=np.uint8)
    off_y = max(0, (height - new_h) // 2)
    off_x = max(0, (width - new_w) // 2)
    canvas[off_y:off_y + new_h, off_x:off_x + new_w] = (resized > 0).astype(np.uint8)
    return canvas


def _extract_char_patches(np_img_rgb: np.ndarray, bbox: Optional[List[int]], template_w: int, template_h: int) -> List[np.ndarray]:
    if cv2 is None or not bbox or template_w <= 0 or template_h <= 0:
        return []
    h, w = np_img_rgb.shape[:2]
    x1, y1, x2, y2 = _clip_bbox(list(bbox), w, h)
    if x2 <= x1 or y2 <= y1:
        return []

    pad_x = max(2, int(round((x2 - x1) * 0.04)))
    pad_y = max(2, int(round((y2 - y1) * 0.08)))
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(w, x2 + pad_x)
    y2 = min(h, y2 + pad_y)
    roi = np_img_rgb[y1:y2, x1:x2]
    if roi.size == 0:
        return []

    gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 40, 40)
    thr = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        33,
        7,
    )
    thr = cv2.morphologyEx(thr, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    thr = cv2.morphologyEx(thr, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))

    found = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = found[0] if len(found) == 2 else found[1]
    if not contours:
        return []

    roi_h, roi_w = thr.shape[:2]
    boxes = []
    for contour in contours:
        cx, cy, cw, ch = cv2.boundingRect(contour)
        if cw <= 0 or ch <= 0:
            continue
        area = cw * ch
        if area < int(roi_w * roi_h * 0.002):
            continue
        if ch < int(roi_h * 0.26):
            continue
        if cw > int(roi_w * 0.48):
            continue
        boxes.append((cx, cy, cw, ch, area))
    if not boxes:
        return []

    boxes.sort(key=lambda item: item[0])
    if len(boxes) > 9:
        boxes = sorted(boxes, key=lambda item: item[4], reverse=True)[:9]
        boxes.sort(key=lambda item: item[0])

    patches: List[np.ndarray] = []
    for cx, cy, cw, ch, _ in boxes:
        char_img = thr[cy:cy + ch, cx:cx + cw]
        if char_img.size == 0:
            continue
        norm = _resize_binary_keep_aspect((char_img > 0).astype(np.uint8), template_w, template_h)
        patches.append(norm)

    slot_patches = _extract_char_patches_by_slots(thr, template_w, template_h)
    if len(patches) < 5:
        return slot_patches

    # Ajusta para 7 caracteres (placa) preservando ordem da esquerda para direita.
    if len(patches) > 7:
        idxs = np.linspace(0, len(patches) - 1, 7).astype(int).tolist()
        patches = [patches[index] for index in idxs]
    elif len(patches) < 7:
        return slot_patches if len(slot_patches) == 7 else []
    return patches[:7]


def _extract_char_patches_by_slots(threshold_binary: np.ndarray, template_w: int, template_h: int) -> List[np.ndarray]:
    if threshold_binary.size == 0:
        return []
    roi_h, roi_w = threshold_binary.shape[:2]
    if roi_h <= 0 or roi_w <= 0:
        return []

    patches: List[np.ndarray] = []
    for index in range(7):
        x1 = int(round((index * roi_w) / 7.0))
        x2 = int(round(((index + 1) * roi_w) / 7.0))
        if x2 <= x1:
            continue
        slot = threshold_binary[:, x1:x2]
        ys, xs = np.where(slot > 0)
        if ys.size > 0 and xs.size > 0:
            y1, y2 = int(ys.min()), int(ys.max())
            sx1, sx2 = int(xs.min()), int(xs.max())
            slot = slot[y1:y2 + 1, sx1:sx2 + 1]
        patch = _resize_binary_keep_aspect((slot > 0).astype(np.uint8), template_w, template_h)
        patches.append(patch)
    return patches if len(patches) == 7 else []


def _template_similarity(char_patch: np.ndarray, template: np.ndarray) -> float:
    if char_patch.shape != template.shape:
        return 0.0
    diff = np.abs(char_patch.astype(np.float32) - template.astype(np.float32))
    return float(1.0 - diff.mean())


def _candidate_template_score(plate: str, char_patches: List[np.ndarray], templates: Dict[str, np.ndarray]) -> float:
    if len(plate) != 7 or len(char_patches) != 7:
        return 0.0
    # Prefixo da placa (3 letras) recebe peso maior para reduzir erros recorrentes.
    weights = (1.35, 1.25, 1.25, 0.95, 1.0, 0.95, 0.95)
    weighted_total = 0.0
    weight_sum = 0.0
    for ch, patch, weight in zip(plate, char_patches, weights):
        template = templates.get(ch)
        if template is None:
            return 0.0
        similarity = _template_similarity(patch, template)
        weighted_total += similarity * float(weight)
        weight_sum += float(weight)
    if weight_sum <= 0:
        return 0.0
    return float(weighted_total / weight_sum)


def _apply_template_rerank(
    candidates: List[Dict],
    np_img_rgb: np.ndarray,
    pipeline: List[str],
) -> Tuple[List[Dict], Optional[str], Optional[Dict]]:
    if not candidates:
        return candidates, None, None

    top_conf = float(candidates[0].get("confidence", 0.0))
    if top_conf >= OCR_TEMPLATE_RERANK_THRESHOLD:
        return candidates, None, None

    templates, meta, err = get_char_templates()
    if err:
        pipeline.append("template_rerank_skipped")
        return candidates, err, None
    assert templates is not None
    assert meta is not None

    template_w = int(meta.get("template_width") or 0)
    template_h = int(meta.get("template_height") or 0)
    if template_w <= 0 or template_h <= 0:
        first_template = next(iter(templates.values()))
        template_h, template_w = first_template.shape[:2]

    anchor_bbox = candidates[0].get("bbox")
    char_patches = _extract_char_patches(np_img_rgb, anchor_bbox, template_w, template_h)
    if len(char_patches) != 7:
        pipeline.append("template_rerank_no_char_patches")
        return candidates, None, {
            "applied": False,
            "reason": "no_char_patches",
            "template_count": len(templates),
        }

    rerank_limit = min(len(candidates), OCR_TEMPLATE_RERANK_TOP_N)
    for item in candidates[:rerank_limit]:
        plate = str(item.get("plate") or "")
        if len(plate) != 7:
            continue
        score = _candidate_template_score(plate, char_patches, templates)
        item["template_score"] = round(score, 4)
        if score >= OCR_TEMPLATE_RERANK_MIN_SCORE:
            boost = min(
                OCR_TEMPLATE_RERANK_BOOST_MAX,
                max(0.0, score - OCR_TEMPLATE_RERANK_MIN_SCORE) * OCR_TEMPLATE_CHAR_MATCH_WEIGHT,
            )
            item["template_boost"] = round(boost, 4)
            item["confidence"] = min(1.0, round(float(item.get("confidence", 0.0)) + boost, 4))
        else:
            item["template_boost"] = 0.0

    reranked = sorted(
        candidates,
        key=lambda x: (float(x.get("confidence", 0.0)), -float(x.get("normalization_penalty", 99.0))),
        reverse=True,
    )
    pipeline.append("template_rerank")
    return reranked, None, {
        "applied": True,
        "template_count": len(templates),
        "template_width": template_w,
        "template_height": template_h,
        "rerank_limit": rerank_limit,
    }


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


def _convert_old_plate_to_mercosul(plate: str) -> Optional[str]:
    value = normalize_text(plate)
    if len(value) != 7 or not PLATE_REGEX_OLD.match(value):
        return None
    mapped = OLD_DIGIT_TO_MERCOSUL_LETTER.get(value[4])
    if not mapped:
        return None
    converted = f"{value[:4]}{mapped}{value[5:]}"
    if not PLATE_REGEX_MERCOSUL.match(converted):
        return None
    return converted


def _normalize_to_mercosul_plate(plate: str) -> Optional[str]:
    value = normalize_text(plate)
    if len(value) != 7:
        return None
    if PLATE_REGEX_MERCOSUL.match(value):
        return value
    if PLATE_REGEX_OLD.match(value):
        return _convert_old_plate_to_mercosul(value)
    return None


def _collapse_to_mercosul_candidates(candidates: List[Dict]) -> List[Dict]:
    by_plate: Dict[str, Dict] = {}
    for raw in candidates:
        plate = str(raw.get("plate") or "")
        pattern = str(raw.get("pattern") or "")
        normalized = _normalize_to_mercosul_plate(plate)
        if not normalized:
            continue

        item = dict(raw)
        item["plate"] = normalized
        item["pattern"] = TEMPLATE_MERCOSUL
        if pattern == TEMPLATE_OLD or PLATE_REGEX_OLD.match(plate):
            item["converted_from_old"] = True
            item["penalty"] = float(item.get("penalty", 0.0)) + OCR_OLD_TO_MERCOSUL_CONVERSION_PENALTY

        prev = by_plate.get(normalized)
        if prev is None or (
            float(item.get("penalty", 99.0)),
            -float(item.get("confidence", 0.0)),
        ) < (
            float(prev.get("penalty", 99.0)),
            -float(prev.get("confidence", 0.0)),
        ):
            by_plate[normalized] = item

    return sorted(
        by_plate.values(),
        key=lambda c: (
            float(c.get("penalty", 99.0)),
            c.get("plate", ""),
        ),
    )


def _enforce_mercosul_scored_candidates(candidates: List[Dict]) -> List[Dict]:
    if not candidates:
        return []

    by_plate: Dict[str, Dict] = {}
    for raw in candidates:
        plate = str(raw.get("plate") or "")
        pattern = str(raw.get("pattern") or "")
        normalized = _normalize_to_mercosul_plate(plate)
        if not normalized:
            continue

        item = dict(raw)
        item["plate"] = normalized
        item["pattern"] = TEMPLATE_MERCOSUL
        if pattern == TEMPLATE_OLD or PLATE_REGEX_OLD.match(plate):
            item["converted_from_old"] = True
            penalty = float(item.get("normalization_penalty", 0.0)) + OCR_OLD_TO_MERCOSUL_CONVERSION_PENALTY
            item["normalization_penalty"] = round(penalty, 3)
            item["confidence"] = max(0.0, round(float(item.get("confidence", 0.0)) - 0.006, 4))

        prev = by_plate.get(normalized)
        if prev is None or (
            float(item.get("confidence", 0.0)),
            -float(item.get("normalization_penalty", 99.0)),
        ) > (
            float(prev.get("confidence", 0.0)),
            -float(prev.get("normalization_penalty", 99.0)),
        ):
            by_plate[normalized] = item

    return sorted(
        by_plate.values(),
        key=lambda x: (float(x.get("confidence", 0.0)), -float(x.get("normalization_penalty", 99.0))),
        reverse=True,
    )


def _normalize_plate_aggressive_local(plate: str) -> str:
    if not plate:
        return plate

    token = normalize_text(plate)
    if len(token) != 7:
        return token

    chars = list(token)

    def to_letter(ch: str) -> str:
        if ch.isalpha():
            return ch
        return LETTER_FROM_DIGIT.get(ch, ch)

    def to_digit(ch: str) -> str:
        if ch.isdigit():
            return ch
        return DIGIT_FROM_LETTER.get(ch, ch)

    for idx in (0, 1, 2):
        chars[idx] = to_letter(chars[idx])
    chars[3] = to_digit(chars[3])
    chars[5] = to_digit(chars[5])
    chars[6] = to_digit(chars[6])

    mercosul = list(chars)
    mercosul[4] = to_letter(mercosul[4])
    mercosul_plate = "".join(mercosul)
    if re.match(r"^[A-Z]{3}[0-9][A-Z][0-9]{2}$", mercosul_plate):
        return mercosul_plate

    old = list(chars)
    old[4] = to_digit(old[4])
    old_plate = "".join(old)
    if re.match(r"^[A-Z]{3}[0-9]{4}$", old_plate):
        converted = _convert_old_plate_to_mercosul(old_plate)
        if converted:
            return converted

    return "".join(chars)


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
    if template == TEMPLATE_MERCOSUL:
        if not PLATE_REGEX_MERCOSUL.match(plate):
            return None
    elif template == TEMPLATE_OLD:
        if not PLATE_REGEX_OLD.match(plate):
            return None
    elif not PLATE_REGEX.match(plate):
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


def _digit_ambiguity_options(index: int, digit: str) -> Tuple[str, ...]:
    options: List[str] = []
    for alt in DIGIT_AMBIGUITY.get(digit, ()):
        if alt != digit and alt not in options:
            options.append(alt)
    for alt in POSITIONAL_DIGIT_AMBIGUITY.get(index, {}).get(digit, ()):
        if alt != digit and alt not in options:
            options.append(alt)
    return tuple(options)


def _digit_change_penalty(index: int, src: str, dst: str) -> float:
    base_cost = float(DIGIT_CHANGE_COST.get((src, dst), 1.0))
    multiplier = float(DIGIT_POSITION_COST_MULTIPLIER.get(index, 1.0))
    return base_cost * multiplier


def _expand_digit_ambiguities(plate: str, pattern: str, base_penalty: int) -> List[Dict]:
    expanded: List[Dict] = []
    seen: set[str] = set()
    digit_slots: List[Tuple[int, str, Tuple[str, ...]]] = []
    for index, expected in enumerate(pattern):
        if expected != "D":
            continue
        current = plate[index]
        alternatives = _digit_ambiguity_options(index, current)
        if alternatives:
            digit_slots.append((index, current, alternatives))
        for alt_digit in alternatives:
            if alt_digit == current:
                continue
            alt_plate = f"{plate[:index]}{alt_digit}{plate[index + 1:]}"
            if not PLATE_REGEX.match(alt_plate):
                continue
            if alt_plate in seen:
                continue
            seen.add(alt_plate)
            expanded.append(
                {
                    "plate": alt_plate,
                    "penalty": float(base_penalty) + _digit_change_penalty(index, current, alt_digit),
                    "pattern": pattern,
                }
            )

    # Expansao de 2 digitos ambiguos para capturar casos com erro duplo (ex.: JBL7D20 -> JBL1D70).
    combo_limit = 36
    combo_count = 0
    for left in range(len(digit_slots)):
        idx_a, src_a, alts_a = digit_slots[left]
        for right in range(left + 1, len(digit_slots)):
            if combo_count >= combo_limit:
                break
            idx_b, src_b, alts_b = digit_slots[right]
            for alt_a in alts_a:
                for alt_b in alts_b:
                    if combo_count >= combo_limit:
                        break
                    chars = list(plate)
                    chars[idx_a] = alt_a
                    chars[idx_b] = alt_b
                    alt_plate = "".join(chars)
                    if not PLATE_REGEX.match(alt_plate):
                        continue
                    if alt_plate in seen:
                        continue
                    seen.add(alt_plate)
                    combo_penalty = (
                        float(base_penalty)
                        + _digit_change_penalty(idx_a, src_a, alt_a)
                        + _digit_change_penalty(idx_b, src_b, alt_b)
                        + 0.24
                    )
                    expanded.append(
                        {
                            "plate": alt_plate,
                            "penalty": combo_penalty,
                            "pattern": pattern,
                        }
                    )
                    combo_count += 1
        if combo_count >= combo_limit:
            break

    return expanded


def _expand_letter_ambiguities(plate: str, pattern: str, base_penalty: int) -> List[Dict]:
    letter_positions = [index for index, expected in enumerate(pattern) if expected == "L"]
    if not letter_positions:
        return []

    # Limita combinacoes para evitar explosao de candidatos.
    max_changes = 3
    max_generated = 120
    options = []
    for index in letter_positions:
        alternatives = tuple(ch for ch in LETTER_AMBIGUITY.get(plate[index], ()) if ch != plate[index])
        if alternatives:
            options.append((index, alternatives))
    if not options:
        return []

    generated: Dict[str, Dict] = {}
    chars = list(plate)

    def visit(position: int, changed_positions: List[int], extra_cost: float):
        if len(generated) >= max_generated:
            return
        if position == len(options):
            if not changed_positions:
                return
            alt_plate = "".join(chars)
            if not PLATE_REGEX.match(alt_plate):
                return
            candidate_penalty = float(base_penalty) + float(extra_cost)
            prev = generated.get(alt_plate)
            if prev is None or candidate_penalty < prev["penalty"]:
                generated[alt_plate] = {
                    "plate": alt_plate,
                    "penalty": candidate_penalty,
                    "pattern": pattern,
                }
            return

        index, alternatives = options[position]
        original = chars[index]

        # Caminho sem alteracao.
        visit(position + 1, changed_positions, extra_cost)

        # Caminhos com alteracao.
        if len(changed_positions) >= max_changes:
            return
        for alt in alternatives:
            chars[index] = alt
            changed_positions.append(index)
            change_cost = float(LETTER_CHANGE_COST.get((original, alt), 1.0))
            if index <= 2:
                change_cost = min(change_cost, 0.45)
            visit(position + 1, changed_positions, extra_cost + change_cost)
            changed_positions.pop()
            chars[index] = original

    visit(0, [], 0.0)
    return sorted(generated.values(), key=lambda item: (item["penalty"], item["plate"]))


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
            if penalty <= 2:
                for alternative in _expand_letter_ambiguities(plate, TEMPLATE_OLD, penalty):
                    _register_candidate(best_by_plate, alternative, template_rank)
        if mercosul:
            plate, penalty = mercosul
            candidate = {"plate": plate, "penalty": penalty, "pattern": TEMPLATE_MERCOSUL}
            _register_candidate(best_by_plate, candidate, template_rank)
            for alternative in _expand_digit_ambiguities(plate, TEMPLATE_MERCOSUL, penalty):
                _register_candidate(best_by_plate, alternative, template_rank)
            if penalty <= 2:
                for alternative in _expand_letter_ambiguities(plate, TEMPLATE_MERCOSUL, penalty):
                    _register_candidate(best_by_plate, alternative, template_rank)

    ranked = sorted(best_by_plate.values(), key=lambda c: (c["penalty"], template_rank[c["pattern"]], c["plate"]))
    return _collapse_to_mercosul_candidates(ranked)


def _extract_aggressive_candidates(text: str) -> List[Dict]:
    if not OCR_AGGRESSIVE_CORRECTION:
        return []
    normalize_fn = normalize_plate_aggressive or _normalize_plate_aggressive_local

    token = normalize_text(text)
    if len(token) < 7:
        return []

    best_by_plate: Dict[str, Dict] = {}
    for i in range(len(token) - 6):
        chunk = token[i:i + 7]
        normalized = normalize_fn(chunk)
        if not normalized or len(normalized) != 7:
            continue
        normalized = normalize_text(normalized)
        normalized_merc = _normalize_to_mercosul_plate(normalized)
        if not normalized_merc:
            continue
        converted_from_old = bool(PLATE_REGEX_OLD.match(normalized))
        base_penalty = OCR_AGGRESSIVE_EXTRA_PENALTY + (
            OCR_OLD_TO_MERCOSUL_CONVERSION_PENALTY if converted_from_old else 0.0
        )
        current = best_by_plate.get(normalized_merc)
        candidate = {
            "plate": normalized_merc,
            "penalty": base_penalty,
            "pattern": TEMPLATE_MERCOSUL,
            "aggressive_normalization": True,
            "converted_from_old": converted_from_old,
        }
        if current is None or float(candidate["penalty"]) < float(current["penalty"]):
            best_by_plate[normalized_merc] = candidate

    return sorted(best_by_plate.values(), key=lambda item: (float(item["penalty"]), item["plate"]))


def _readtext_with_plate_profile(
    reader,
    image: np.ndarray,
    decoder: str,
    beam_width: int,
):
    kwargs = {
        "detail": 1,
        "paragraph": False,
        "allowlist": OCR_PLATE_ALLOWLIST,
        "decoder": decoder,
        "beamWidth": beam_width,
        "min_size": 8,
        "contrast_ths": 0.08,
        "adjust_contrast": 0.70,
        "text_threshold": 0.55,
        "low_text": 0.25,
        "link_threshold": 0.20,
        "mag_ratio": 1.2,
    }
    try:
        return reader.readtext(image, **kwargs)
    except TypeError:
        # Compatibilidade com versões do EasyOCR sem todos os kwargs acima.
        return reader.readtext(
            image,
            detail=1,
            paragraph=False,
            allowlist=OCR_PLATE_ALLOWLIST,
            decoder=decoder,
            beamWidth=beam_width,
        )


def _bbox_from_easyocr(box: List[List[float]], offset: Tuple[int, int]) -> Optional[List[int]]:
    local_bbox = _bbox_from_easyocr_local(box)
    if not local_bbox:
        return None
    x1, y1, x2, y2 = local_bbox
    ox, oy = offset
    return [x1 + ox, y1 + oy, x2 + ox, y2 + oy]


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

        scan_modes = [("greedy", 1, 0.0)]
        if (
            variant_index < OCR_BEAMSEARCH_MAX_VARIANTS
            and (source.startswith("yolo") or pixels <= OCR_BEAMSEARCH_MAX_PIXELS)
        ):
            scan_modes.append(("beamsearch", OCR_BEAMSEARCH_WIDTH, 0.012))

        for decoder, beam_width, decoder_boost in scan_modes:
            if _is_deadline_reached(deadline_at):
                break
            try:
                read = _readtext_with_plate_profile(
                    reader,
                    variant,
                    decoder=decoder,
                    beam_width=beam_width,
                )
            except Exception:
                continue

            for box, text, conf in read:
                if float(conf) < min_conf and not source.startswith("yolo"):
                    continue
                normalized_text = normalize_text(text)
                if _is_non_plate_short_token(normalized_text):
                    continue
                if source.startswith("yolo_box_") and len(normalized_text) > OCR_YOLO_OCR_TOKEN_MAX_LEN:
                    continue
                local_bbox = _bbox_from_easyocr_local(box)
                if not _is_plausible_plate_text_box(
                    local_bbox,
                    image_width=variant.shape[1],
                    image_height=variant.shape[0],
                    source=source,
                ):
                    continue
                matches = extract_plate_candidates(text)
                if not matches:
                    matches = _extract_aggressive_candidates(text)
                if not matches:
                    continue
                bbox = _bbox_from_easyocr(box, offset)
                for match in matches:
                    plate = match["plate"]
                    penalty = float(match["penalty"])
                    pattern = match.get("pattern")
                    score = float(conf)
                    score += source_boost
                    if source_confidence is not None:
                        score += float(source_confidence) * 0.10
                    score += float(variant_boost)
                    score += float(decoder_boost)
                    score += _pattern_score_adjustment(str(pattern) if pattern else None)
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
                        "ocr_decoder": decoder,
                        "normalization_penalty": round(penalty, 3),
                        "pattern": pattern,
                        "aggressive_normalization": bool(match.get("aggressive_normalization")),
                    })
        if _has_strong_candidate(detections):
            break
    return detections


def _fallback_regions(np_img_rgb: np.ndarray) -> List[Tuple[str, np.ndarray, Tuple[int, int]]]:
    h, w = np_img_rgb.shape[:2]
    regions = []
    center_x1, center_x2 = w // 4, (w * 3) // 4
    # Prioriza centro/meio quando YOLO está indisponível; mantém regiões inferiores no fluxo.
    regions.append(("center_mid", np_img_rgb[h // 3:h, center_x1:center_x2], (center_x1, h // 3)))
    regions.append(("middle_band", np_img_rgb[h // 3:(h * 2) // 3, 0:w], (0, h // 3)))
    regions.append(("center_bottom", np_img_rgb[h // 2:h, center_x1:center_x2], (center_x1, h // 2)))
    regions.append(("bottom_half", np_img_rgb[h // 2:h, 0:w], (0, h // 2)))
    regions.append(("bottom_third", np_img_rgb[(h * 2) // 3:h, 0:w], (0, (h * 2) // 3)))
    regions.append(("full", np_img_rgb, (0, 0)))
    return regions


def _fallback_regions_no_yolo(np_img_rgb: np.ndarray) -> List[Tuple[str, np.ndarray, Tuple[int, int]]]:
    h, w = np_img_rgb.shape[:2]
    regions = []
    center_x1, center_x2 = w // 4, (w * 3) // 4
    half_y = h // 2
    top_two_thirds = (h * 2) // 3
    lower_band_y1 = int(round(h * 0.45))
    lower_band_y2 = int(round(h * 0.82))

    # Sem detector de placa, prioriza recortes menores no topo/centro para
    # manter detalhe de caracteres e reduzir custo do OCR.
    regions.append(("noyolo_mid_center", np_img_rgb[h // 4:top_two_thirds, center_x1:center_x2], (center_x1, h // 4)))
    regions.append(("center_bottom", np_img_rgb[h // 2:h, center_x1:center_x2], (center_x1, h // 2)))
    regions.append(("noyolo_lower_band", np_img_rgb[lower_band_y1:lower_band_y2, 0:w], (0, lower_band_y1)))
    regions.append(("bottom_half", np_img_rgb[h // 2:h, 0:w], (0, h // 2)))
    regions.append(("noyolo_top_center", np_img_rgb[0:half_y, center_x1:center_x2], (center_x1, 0)))
    regions.append(("center_mid", np_img_rgb[h // 3:h, center_x1:center_x2], (center_x1, h // 3)))
    regions.append(("middle_band", np_img_rgb[h // 3:(h * 2) // 3, 0:w], (0, h // 3)))
    regions.append(("full", np_img_rgb, (0, 0)))
    return regions


def _plate_contour_regions(
    np_img_rgb: np.ndarray,
    max_ms: int = OCR_CONTOUR_MAX_MS,
) -> List[Tuple[str, np.ndarray, Tuple[int, int]]]:
    if cv2 is None:
        return []

    h, w = np_img_rgb.shape[:2]
    if h <= 0 or w <= 0:
        return []

    started = perf_counter()
    budget_s = (max(0, int(max_ms)) / 1000.0) if max_ms > 0 else 0.0

    def timed_out() -> bool:
        return budget_s > 0 and (perf_counter() - started) >= budget_s

    roi_start_y = int(round(h * OCR_CONTOUR_ROI_START_RATIO))
    roi_start_y = max(0, min(h - 1, roi_start_y))
    roi = np_img_rgb[roi_start_y:h, 0:w]
    if roi.size == 0:
        roi = np_img_rgb
        roi_start_y = 0

    gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
    # Gaussian blur e mais leve que bilateral para esse passo de proposal.
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 70, 180)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    if timed_out():
        return []

    found = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = found[0] if len(found) == 2 else found[1]
    if not contours:
        if roi_start_y > 0 and not timed_out():
            gray_full = cv2.cvtColor(np_img_rgb, cv2.COLOR_RGB2GRAY)
            gray_full = cv2.GaussianBlur(gray_full, (5, 5), 0)
            edges_full = cv2.Canny(gray_full, 70, 180)
            edges_full = cv2.dilate(edges_full, np.ones((3, 3), np.uint8), iterations=1)
            found_full = cv2.findContours(edges_full, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = found_full[0] if len(found_full) == 2 else found_full[1]
            roi_start_y = 0
            if not contours:
                return []
        else:
            return []

    if timed_out():
        return []

    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    if OCR_CONTOUR_SCAN_MAX > 0:
        contours = contours[:OCR_CONTOUR_SCAN_MAX]
    regions: List[Tuple[str, np.ndarray, Tuple[int, int]]] = []
    seen_boxes: List[Tuple[int, int, int, int]] = []

    def overlaps(box_a: Tuple[int, int, int, int], box_b: Tuple[int, int, int, int]) -> bool:
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b
        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return False
        inter = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
        area_b = max(1, (bx2 - bx1) * (by2 - by1))
        iou = inter / float(area_a + area_b - inter)
        return iou >= 0.45

    for contour in contours:
        if timed_out():
            break
        x, y, bw, bh = cv2.boundingRect(contour)
        y += roi_start_y
        if bw <= 0 or bh <= 0:
            continue

        aspect = bw / float(bh)
        area_ratio = (bw * bh) / float(w * h)
        center_y_ratio = (y + (bh / 2.0)) / float(h)
        if aspect < 2.0 or aspect > 8.8:
            continue
        if area_ratio < 0.0025 or area_ratio > 0.22:
            continue
        if center_y_ratio < 0.22:
            continue

        pad_x = int(round(bw * 0.12))
        pad_y = int(round(bh * 0.20))
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(w, x + bw + pad_x)
        y2 = min(h, y + bh + pad_y)
        if x2 <= x1 or y2 <= y1:
            continue

        box = (x1, y1, x2, y2)
        if any(overlaps(box, prev) for prev in seen_boxes):
            continue

        crop = np_img_rgb[y1:y2, x1:x2]
        if crop.size == 0:
            continue

        seen_boxes.append(box)
        regions.append((f"contour_plate_{len(regions)}", crop, (x1, y1)))
        if len(regions) >= OCR_CONTOUR_MAX_REGIONS:
            break

    return regions


def _dedupe_candidates(
    candidates: List[Dict],
    width: int,
    height: int,
    limit: Optional[int] = None,
) -> List[Dict]:
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
        position_boost = _position_score_adjustment(best_item.get("bbox"), width, height)
        total_boost = support_boost + position_boost
        best_item["support_hits"] = hits
        best_item["support_sources"] = source_count
        best_item["support_boost"] = round(support_boost, 4)
        best_item["position_boost"] = round(position_boost, 4)
        best_item["confidence"] = min(1.0, round(float(best_item["confidence"]) + total_boost, 4))
        deduped.append(best_item)

    deduped.sort(
        key=lambda x: (x["confidence"], -x.get("normalization_penalty", 99)),
        reverse=True,
    )
    if limit is not None and limit > 0:
        return deduped[:limit]
    return deduped


def _has_strong_candidate(candidates: List[Dict]) -> bool:
    if not candidates:
        return False
    best = max(
        candidates,
        key=lambda item: (
            float(item.get("confidence", 0.0)),
            -float(item.get("normalization_penalty", 99.0)),
        ),
    )
    return (
        float(best.get("confidence", 0.0)) >= OCR_STRONG_CONFIDENCE
        and float(best.get("normalization_penalty", 99.0)) <= 1.0
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

    first_conf = float(first.get("confidence", 0.0))
    second_conf = float(second.get("confidence", 0.0))
    conf_gap = abs(first_conf - second_conf)

    if first_plate[:6] == second_plate[:6]:
        return conf_gap <= OCR_AMBIGUOUS_DELTA

    if _is_middle_char_letter_digit_ambiguous_pair(first_plate, second_plate):
        return conf_gap <= OCR_AMBIGUOUS_DELTA

    if _is_middle_letter_o_d_ambiguous_pair(first_plate, second_plate):
        return conf_gap <= OCR_MIDDLE_O_D_AMBIGUOUS_DELTA

    if _is_penultimate_digit_two_ambiguous_pair(first_plate, second_plate):
        return conf_gap <= OCR_PENULTIMATE_2_AMBIGUOUS_DELTA

    if _is_prefix_letter_ambiguous_pair(first_plate, second_plate):
        return conf_gap <= OCR_PREFIX_AMBIGUOUS_DELTA

    return False


def _is_prefix_letter_ambiguous_pair(plate_a: str, plate_b: str) -> bool:
    if len(plate_a) != 7 or len(plate_b) != 7:
        return False
    if plate_a[3:] != plate_b[3:]:
        return False

    changed = 0
    for index in range(3):
        ch_a = plate_a[index]
        ch_b = plate_b[index]
        if ch_a == ch_b:
            continue
        if ch_b not in LETTER_AMBIGUITY.get(ch_a, ()) and ch_a not in LETTER_AMBIGUITY.get(ch_b, ()):
            return False
        changed += 1

    if changed == 0:
        return False

    # Nao abre ambiguidade se a diferenca de score estiver muito alta.
    # Isso evita bloquear casos em que um candidato e nitidamente superior.
    return True


def _is_penultimate_digit_two_ambiguous_pair(plate_a: str, plate_b: str) -> bool:
    if len(plate_a) != 7 or len(plate_b) != 7:
        return False
    if plate_a[:5] != plate_b[:5] or plate_a[6] != plate_b[6]:
        return False
    pair = {plate_a[5], plate_b[5]}
    return pair == {"2", "9"}


def _is_middle_letter_o_d_ambiguous_pair(plate_a: str, plate_b: str) -> bool:
    if len(plate_a) != 7 or len(plate_b) != 7:
        return False
    if plate_a[:4] != plate_b[:4] or plate_a[5:] != plate_b[5:]:
        return False
    pair = {plate_a[4], plate_b[4]}
    return pair == {"O", "D"}


def _is_middle_char_letter_digit_ambiguous_pair(plate_a: str, plate_b: str) -> bool:
    if len(plate_a) != 7 or len(plate_b) != 7:
        return False
    if plate_a[:4] != plate_b[:4] or plate_a[5:] != plate_b[5:]:
        return False
    c1 = plate_a[4]
    c2 = plate_b[4]
    if c1 == c2:
        return False
    if c1.isdigit() and LETTER_FROM_DIGIT.get(c1) == c2:
        return True
    if c2.isdigit() and LETTER_FROM_DIGIT.get(c2) == c1:
        return True
    if c1.isalpha() and DIGIT_FROM_LETTER.get(c1) == c2:
        return True
    if c2.isalpha() and DIGIT_FROM_LETTER.get(c2) == c1:
        return True
    return False


def _is_low_certainty_best(candidates: List[Dict]) -> bool:
    if not candidates:
        return False

    best = candidates[0]
    conf = float(best.get("confidence", 0.0))
    hits = int(best.get("support_hits", 1) or 1)
    penalty = float(best.get("normalization_penalty", 99.0))
    source = str(best.get("source") or "")
    decoder = str(best.get("ocr_decoder") or "")
    aggressive = bool(best.get("aggressive_normalization"))
    raw_ocr_conf = float(best.get("ocr_confidence", 0.0))
    template_score = float(best.get("template_score", 0.0)) if best.get("template_score") is not None else 0.0

    if conf < 0.62:
        return True
    if conf < OCR_LOW_CERTAINTY_SINGLE_HIT_CONFIDENCE and hits <= 1:
        return True
    if source.startswith("yolo_box_") and hits <= 1 and conf < OCR_LOW_CERTAINTY_YOLO_SINGLE_HIT_CONFIDENCE:
        return True
    if decoder == "beamsearch" and hits <= 1 and conf < OCR_LOW_CERTAINTY_BEAM_CONFIDENCE:
        return True
    if aggressive and conf < OCR_LOW_CERTAINTY_AGGRESSIVE_CONFIDENCE:
        return True
    if raw_ocr_conf > 0 and raw_ocr_conf < OCR_LOW_CERTAINTY_RAW_OCR_CONFIDENCE and conf < 0.90:
        return True
    if template_score > 0 and template_score < OCR_LOW_CERTAINTY_TEMPLATE_SCORE and conf < 0.90:
        return True
    if penalty >= 2 and conf < 0.80:
        return True
    if source in ("full", "middle_band", "rescue_full") and conf < 0.86:
        return True
    if len(candidates) >= 2:
        second_conf = float(candidates[1].get("confidence", 0.0))
        if (conf - second_conf) <= OCR_LOW_CERTAINTY_SMALL_GAP and conf < 0.90:
            return True
    return False


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
        allowed_delta = OCR_ZERO_PRIORITY_DELTA
        source = str(item.get("source") or "")
        if (
            plate[5] == "9"
            and seven_conf < 0.90
            and not source.startswith("yolo_box_")
        ):
            allowed_delta = max(allowed_delta, OCR_ZERO_PRIORITY_PENULTIMATE_NINE_NO_YOLO_DELTA)

        if (seven_conf - zero_conf) > allowed_delta:
            continue

        seven_penalty = float(item.get("normalization_penalty", 99.0))
        zero_penalty = float(zero_candidate.get("normalization_penalty", 99.0))
        if (zero_penalty - seven_penalty) > 1:
            continue

        chosen = ordered.pop(zero_idx)
        ordered.insert(idx, chosen)
        return ordered, True

    return ordered, False


def _prioritize_mercosul_middle_letter(candidates: List[Dict]) -> Tuple[List[Dict], bool]:
    if len(candidates) < 2:
        return candidates, False

    ordered = list(candidates)
    for idx, item in enumerate(ordered):
        plate = str(item.get("plate") or "")
        if len(plate) != 7 or not plate[4].isdigit():
            continue

        letter_variant = LETTER_FROM_DIGIT.get(plate[4])
        if not letter_variant:
            continue

        mercosul_plate = f"{plate[:4]}{letter_variant}{plate[5:]}"
        letter_idx = next(
            (index for index, candidate in enumerate(ordered) if str(candidate.get("plate") or "") == mercosul_plate),
            None,
        )
        if letter_idx is None or letter_idx < idx:
            continue

        digit_conf = float(item.get("confidence", 0.0))
        letter_candidate = ordered[letter_idx]
        letter_conf = float(letter_candidate.get("confidence", 0.0))
        if (digit_conf - letter_conf) > OCR_MERCOSUL_MIDDLE_PRIORITY_DELTA:
            continue

        digit_penalty = float(item.get("normalization_penalty", 99.0))
        letter_penalty = float(letter_candidate.get("normalization_penalty", 99.0))
        if (letter_penalty - digit_penalty) > 1:
            continue

        chosen = ordered.pop(letter_idx)
        ordered.insert(idx, chosen)
        return ordered, True

    return ordered, False


def _prioritize_prefix_y_over_v(candidates: List[Dict]) -> Tuple[List[Dict], bool]:
    if len(candidates) < 2:
        return candidates, False

    ordered = list(candidates)
    for idx, item in enumerate(ordered):
        plate = str(item.get("plate") or "")
        if len(plate) != 7:
            continue

        for pos in range(3):
            if plate[pos] != "V":
                continue
            y_variant = f"{plate[:pos]}Y{plate[pos + 1:]}"
            y_idx = next(
                (index for index, candidate in enumerate(ordered) if str(candidate.get("plate") or "") == y_variant),
                None,
            )
            if y_idx is None or y_idx < idx:
                continue

            v_conf = float(item.get("confidence", 0.0))
            y_candidate = ordered[y_idx]
            y_conf = float(y_candidate.get("confidence", 0.0))
            if (v_conf - y_conf) > OCR_PREFIX_Y_OVER_V_PRIORITY_DELTA:
                continue

            v_penalty = float(item.get("normalization_penalty", 99.0))
            y_penalty = float(y_candidate.get("normalization_penalty", 99.0))
            if (y_penalty - v_penalty) > 1:
                continue

            chosen = ordered.pop(y_idx)
            ordered.insert(idx, chosen)
            return ordered, True

    return ordered, False


def _prioritize_fourth_digit_one_over_seven(candidates: List[Dict]) -> Tuple[List[Dict], bool]:
    if len(candidates) < 2:
        return candidates, False

    ordered = list(candidates)
    for idx, item in enumerate(ordered):
        plate = str(item.get("plate") or "")
        if len(plate) != 7 or plate[3] != "7":
            continue

        preferred_plate = f"{plate[:3]}1{plate[4:]}"
        preferred_idx = next(
            (index for index, candidate in enumerate(ordered) if str(candidate.get("plate") or "") == preferred_plate),
            None,
        )
        if preferred_idx is None or preferred_idx < idx:
            continue

        current_conf = float(item.get("confidence", 0.0))
        preferred_candidate = ordered[preferred_idx]
        preferred_conf = float(preferred_candidate.get("confidence", 0.0))
        if (current_conf - preferred_conf) > OCR_FOURTH_7_PRIORITY_DELTA:
            continue

        current_penalty = float(item.get("normalization_penalty", 99.0))
        preferred_penalty = float(preferred_candidate.get("normalization_penalty", 99.0))
        if (preferred_penalty - current_penalty) > 1:
            continue

        chosen = ordered.pop(preferred_idx)
        ordered.insert(idx, chosen)
        return ordered, True

    return ordered, False


def _prioritize_penultimate_digit_from_two(candidates: List[Dict]) -> Tuple[List[Dict], bool]:
    if len(candidates) < 2:
        return candidates, False

    ordered = list(candidates)
    for idx, item in enumerate(ordered):
        plate = str(item.get("plate") or "")
        if len(plate) != 7 or plate[5] != "2":
            continue

        variants = (f"{plate[:5]}9{plate[6:]}", f"{plate[:5]}7{plate[6:]}")
        best_idx = None
        best_conf = -1.0
        for variant in variants:
            variant_idx = next(
                (index for index, candidate in enumerate(ordered) if str(candidate.get("plate") or "") == variant),
                None,
            )
            if variant_idx is None or variant_idx < idx:
                continue
            variant_conf = float(ordered[variant_idx].get("confidence", 0.0))
            if variant_conf > best_conf:
                best_conf = variant_conf
                best_idx = variant_idx

        if best_idx is None:
            continue

        current_conf = float(item.get("confidence", 0.0))
        if (current_conf - best_conf) > OCR_PENULTIMATE_2_PRIORITY_DELTA:
            continue

        current_penalty = float(item.get("normalization_penalty", 99.0))
        preferred_penalty = float(ordered[best_idx].get("normalization_penalty", 99.0))
        if (preferred_penalty - current_penalty) > 1:
            continue

        chosen = ordered.pop(best_idx)
        ordered.insert(idx, chosen)
        return ordered, True

    return ordered, False


def _prioritize_fourth_digit_four_over_one(candidates: List[Dict]) -> Tuple[List[Dict], bool]:
    if not OCR_ENABLE_FOURTH_1_4_PRIORITY:
        return candidates, False

    if len(candidates) < 2:
        return candidates, False

    ordered = list(candidates)
    for idx, item in enumerate(ordered):
        plate = str(item.get("plate") or "")
        if len(plate) != 7 or plate[3] != "1":
            continue

        preferred_plate = f"{plate[:3]}4{plate[4:]}"
        preferred_idx = next(
            (index for index, candidate in enumerate(ordered) if str(candidate.get("plate") or "") == preferred_plate),
            None,
        )
        if preferred_idx is None or preferred_idx < idx:
            continue

        current_conf = float(item.get("confidence", 0.0))
        preferred_candidate = ordered[preferred_idx]
        preferred_conf = float(preferred_candidate.get("confidence", 0.0))
        if (current_conf - preferred_conf) > OCR_FOURTH_1_4_PRIORITY_DELTA:
            continue

        current_penalty = float(item.get("normalization_penalty", 99.0))
        preferred_penalty = float(preferred_candidate.get("normalization_penalty", 99.0))
        if (preferred_penalty - current_penalty) > 1:
            continue

        chosen = ordered.pop(preferred_idx)
        ordered.insert(idx, chosen)
        return ordered, True

    return ordered, False


def _prioritize_penultimate_digit_nine_over_zero(candidates: List[Dict]) -> Tuple[List[Dict], bool]:
    if len(candidates) < 2:
        return candidates, False

    ordered = list(candidates)
    for idx, item in enumerate(ordered):
        plate = str(item.get("plate") or "")
        if len(plate) != 7 or plate[5] != "0":
            continue

        preferred_plate = f"{plate[:5]}9{plate[6:]}"
        preferred_idx = next(
            (index for index, candidate in enumerate(ordered) if str(candidate.get("plate") or "") == preferred_plate),
            None,
        )
        if preferred_idx is None or preferred_idx < idx:
            continue

        current_conf = float(item.get("confidence", 0.0))
        preferred_candidate = ordered[preferred_idx]
        preferred_conf = float(preferred_candidate.get("confidence", 0.0))
        if (current_conf - preferred_conf) > OCR_PENULTIMATE_0_9_PRIORITY_DELTA:
            continue

        current_penalty = float(item.get("normalization_penalty", 99.0))
        preferred_penalty = float(preferred_candidate.get("normalization_penalty", 99.0))
        if (preferred_penalty - current_penalty) > OCR_PENULTIMATE_0_9_PRIORITY_MAX_PENALTY_GAP:
            continue

        current_template = float(item.get("template_score", 0.0) or 0.0)
        preferred_template = float(preferred_candidate.get("template_score", 0.0) or 0.0)
        if current_template > 0 and preferred_template > 0:
            if (preferred_template - current_template) < OCR_PENULTIMATE_0_9_PRIORITY_MIN_TEMPLATE_DIFF:
                continue

        chosen = ordered.pop(preferred_idx)
        ordered.insert(idx, chosen)
        return ordered, True

    return ordered, False


def _prioritize_penultimate_digit_by_penalty(candidates: List[Dict]) -> Tuple[List[Dict], bool]:
    if len(candidates) < 2:
        return candidates, False

    ordered = list(candidates)
    for idx, item in enumerate(ordered):
        plate = str(item.get("plate") or "")
        if len(plate) != 7 or plate[5] not in {"0", "9"}:
            continue

        preferred_digit = "9" if plate[5] == "0" else "0"
        preferred_plate = f"{plate[:5]}{preferred_digit}{plate[6:]}"
        preferred_idx = next(
            (index for index, candidate in enumerate(ordered) if str(candidate.get("plate") or "") == preferred_plate),
            None,
        )
        if preferred_idx is None or preferred_idx < idx:
            continue

        current_conf = float(item.get("confidence", 0.0))
        preferred_candidate = ordered[preferred_idx]
        preferred_conf = float(preferred_candidate.get("confidence", 0.0))
        if abs(current_conf - preferred_conf) > OCR_PENULTIMATE_0_9_LOW_PENALTY_CONF_GAP_MAX:
            continue

        current_penalty = float(item.get("normalization_penalty", 99.0))
        preferred_penalty = float(preferred_candidate.get("normalization_penalty", 99.0))
        if (current_penalty - preferred_penalty) < OCR_PENULTIMATE_0_9_LOW_PENALTY_GAP_MIN:
            continue

        chosen = ordered.pop(preferred_idx)
        ordered.insert(idx, chosen)
        return ordered, True

    return ordered, False


def _prioritize_middle_letter_d_over_o(candidates: List[Dict]) -> Tuple[List[Dict], bool]:
    if len(candidates) < 2:
        return candidates, False

    ordered = list(candidates)
    for idx, item in enumerate(ordered):
        plate = str(item.get("plate") or "")
        if len(plate) != 7 or plate[4] != "O":
            continue

        preferred_plate = f"{plate[:4]}D{plate[5:]}"
        preferred_idx = next(
            (index for index, candidate in enumerate(ordered) if str(candidate.get("plate") or "") == preferred_plate),
            None,
        )
        if preferred_idx is None or preferred_idx < idx:
            continue

        current_conf = float(item.get("confidence", 0.0))
        preferred_candidate = ordered[preferred_idx]
        preferred_conf = float(preferred_candidate.get("confidence", 0.0))
        if (current_conf - preferred_conf) > OCR_MIDDLE_O_D_PRIORITY_DELTA:
            continue

        current_penalty = float(item.get("normalization_penalty", 99.0))
        preferred_penalty = float(preferred_candidate.get("normalization_penalty", 99.0))
        if (preferred_penalty - current_penalty) > 1:
            continue

        chosen = ordered.pop(preferred_idx)
        ordered.insert(idx, chosen)
        return ordered, True

    return ordered, False


def _inject_middle_letter_d_from_o(candidates: List[Dict]) -> Tuple[List[Dict], bool]:
    if not candidates:
        return candidates, False

    existing = {str(item.get("plate") or "") for item in candidates}
    injected: List[Dict] = []

    for item in candidates:
        plate = str(item.get("plate") or "")
        if len(plate) != 7 or plate[4] != "O":
            continue
        d_plate = f"{plate[:4]}D{plate[5:]}"
        if d_plate in existing:
            continue

        clone = dict(item)
        clone["plate"] = d_plate
        clone["confidence"] = min(
            1.0,
            round(float(item.get("confidence", 0.0)) + OCR_MIDDLE_O_D_INJECT_CONF_BOOST, 4),
        )
        clone["normalization_penalty"] = round(
            float(item.get("normalization_penalty", 0.0)) + OCR_MIDDLE_O_D_INJECT_PENALTY_DELTA,
            3,
        )
        clone["source"] = f"{str(item.get('source') or 'unknown')}:od_injected"
        clone["od_injected"] = True
        injected.append(clone)
        existing.add(d_plate)

    if not injected:
        return candidates, False

    merged = list(candidates) + injected
    merged.sort(
        key=lambda x: (
            float(x.get("confidence", 0.0)),
            -float(x.get("normalization_penalty", 99.0)),
        ),
        reverse=True,
    )
    return merged, True


def _inject_last_digit_zero_from_seven(candidates: List[Dict]) -> Tuple[List[Dict], bool]:
    if not candidates:
        return candidates, False

    best_conf_by_plate: Dict[str, float] = {}
    for item in candidates:
        plate = str(item.get("plate") or "")
        if not plate:
            continue
        conf = float(item.get("confidence", 0.0))
        prev = best_conf_by_plate.get(plate)
        if prev is None or conf > prev:
            best_conf_by_plate[plate] = conf

    injected: List[Dict] = []

    for item in candidates:
        plate = str(item.get("plate") or "")
        if len(plate) != 7 or plate[5] != "9" or plate[6] != "7":
            continue

        source = str(item.get("source") or "")
        if source.startswith("yolo_box_"):
            continue

        conf = float(item.get("confidence", 0.0))
        if conf > OCR_LAST_7_TO_0_INJECT_MAX_CONFIDENCE:
            continue

        decoder = str(item.get("ocr_decoder") or "")
        raw_ocr_conf = float(item.get("ocr_confidence", 0.0))
        if decoder != "beamsearch":
            continue
        if raw_ocr_conf > OCR_LAST_7_TO_0_INJECT_MAX_RAW_OCR_CONFIDENCE:
            continue

        zero_plate = f"{plate[:6]}0"

        injected_conf = min(
            1.0,
            round(conf + OCR_LAST_7_TO_0_INJECT_CONF_BOOST, 4),
        )
        existing_zero_conf = best_conf_by_plate.get(zero_plate)
        if existing_zero_conf is not None and existing_zero_conf >= (injected_conf - 0.004):
            continue

        clone = dict(item)
        clone["plate"] = zero_plate
        clone["confidence"] = injected_conf
        clone["normalization_penalty"] = round(
            float(item.get("normalization_penalty", 0.0)) + OCR_LAST_7_TO_0_INJECT_PENALTY_DELTA,
            3,
        )
        clone["source"] = f"{source or 'unknown'}:70_injected"
        clone["last_digit_70_injected"] = True
        injected.append(clone)
        best_conf_by_plate[zero_plate] = injected_conf

    if not injected:
        return candidates, False

    merged = list(candidates) + injected
    merged.sort(
        key=lambda x: (
            float(x.get("confidence", 0.0)),
            -float(x.get("normalization_penalty", 99.0)),
        ),
        reverse=True,
    )
    return merged, True


def _prioritize_lower_penalty_same_shell(candidates: List[Dict]) -> Tuple[List[Dict], bool]:
    if len(candidates) < 2:
        return candidates, False

    ordered = list(candidates)
    for idx, item in enumerate(ordered):
        plate = str(item.get("plate") or "")
        if len(plate) != 7:
            continue

        shell = f"{plate[:3]}:{plate[5:]}"
        current_conf = float(item.get("confidence", 0.0))
        current_penalty = float(item.get("normalization_penalty", 99.0))

        preferred_idx = None
        preferred_penalty = current_penalty
        for cand_idx, cand in enumerate(ordered):
            if cand_idx <= idx:
                continue
            cand_plate = str(cand.get("plate") or "")
            if len(cand_plate) != 7:
                continue
            cand_shell = f"{cand_plate[:3]}:{cand_plate[5:]}"
            if cand_shell != shell:
                continue

            diff_positions = [pos for pos in range(7) if plate[pos] != cand_plate[pos]]
            if len(diff_positions) != 1 or diff_positions[0] != 3:
                continue
            if {plate[3], cand_plate[3]} != {"1", "7"}:
                continue

            cand_conf = float(cand.get("confidence", 0.0))
            if (current_conf - cand_conf) > OCR_LOW_PENALTY_PRIORITY_CONF_GAP_MAX:
                continue

            cand_penalty = float(cand.get("normalization_penalty", 99.0))
            if (current_penalty - cand_penalty) < OCR_LOW_PENALTY_PRIORITY_PENALTY_GAP_MIN:
                continue

            if cand_penalty < preferred_penalty:
                preferred_penalty = cand_penalty
                preferred_idx = cand_idx

        if preferred_idx is not None:
            chosen = ordered.pop(preferred_idx)
            ordered.insert(idx, chosen)
            return ordered, True

    return ordered, False


def recognize_plate(img: Image.Image, progress_cb=None) -> dict:
    _emit = lambda pct, stage: progress_cb(pct, stage) if callable(progress_cb) else None  # noqa: E731
    started = perf_counter()
    deadline_at = (started + (OCR_MAX_PROCESS_MS / 1000.0)) if OCR_MAX_PROCESS_MS > 0 else None
    timeout_reached = False
    np_img_original = np.array(img.convert("RGB"))
    height, width = np_img_original.shape[:2]
    np_img_rgb, process_scale = _resize_for_processing(np_img_original)
    proc_height, proc_width = np_img_rgb.shape[:2]
    _emit(5, "decode")

    pipeline = []
    candidates = []
    timings = {}
    contour_candidates_weak = False

    yolo_model, yolo_model_path, yolo_err = get_yolo_model()
    _emit(12, "yolo_load")
    if yolo_model is not None and not _is_deadline_reached(deadline_at):
        yolo_started = perf_counter()
        try:
            _emit(18, "yolo_predict")
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
                    if not _is_plausible_yolo_detection_box([x1, y1, x2, y2], proc_width, proc_height):
                        pipeline.append(f"yolo_box_rejected:{index}")
                        continue
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
            _emit(45, "yolo_ocr")
    else:
        pipeline.append("yolo_unavailable")
        _emit(45, "yolo_skipped")

    if not candidates and not _is_deadline_reached(deadline_at):
        contour_started = perf_counter()
        contour_regions = _plate_contour_regions(np_img_rgb, max_ms=OCR_CONTOUR_MAX_MS)
        if contour_regions:
            pipeline.append("contour_plate_regions")
            for region_name, region_img, offset in contour_regions:
                if _is_deadline_reached(deadline_at):
                    timeout_reached = True
                    pipeline.append("deadline_reached:contour_regions")
                    break
                if OCR_CONTOUR_MAX_MS > 0 and ((perf_counter() - contour_started) * 1000.0) >= OCR_CONTOUR_MAX_MS:
                    pipeline.append("contour_budget_reached")
                    break
                contour_candidates = _ocr_scan(
                    region_img,
                    source=region_name,
                    offset=offset,
                    deadline_at=deadline_at,
                    max_variants=OCR_CONTOUR_OCR_MAX_VARIANTS,
                    min_text_confidence=0.10,
                )
                candidates.extend(contour_candidates)
                if _has_strong_candidate(contour_candidates):
                    pipeline.append(f"contour_short_circuit:{region_name}")
                    break
        timings["contour_ms"] = int(round((perf_counter() - contour_started) * 1000))
        if candidates:
            best_contour_conf = max(float(item.get("confidence", 0.0)) for item in candidates)
            best_contour_raw_conf = max(float(item.get("ocr_confidence", 0.0)) for item in candidates)
            if (
                best_contour_conf < OCR_CONTOUR_ACCEPT_CONFIDENCE
                or best_contour_raw_conf < OCR_CONTOUR_ACCEPT_RAW_CONFIDENCE
            ):
                contour_candidates_weak = True
                pipeline.append("contour_candidates_weak")
                candidates = []
        _emit(62, "contour")

    if (not candidates or contour_candidates_weak) and not _is_deadline_reached(deadline_at):
        fallback_started = perf_counter()
        pipeline.append("fallback_ocr_regions")
        regions = _fallback_regions_no_yolo(np_img_rgb) if yolo_model is None else _fallback_regions(np_img_rgb)
        fallback_stage_deadline = None
        if yolo_model is None and OCR_NO_YOLO_FALLBACK_MAX_MS > 0:
            fallback_stage_deadline = fallback_started + (OCR_NO_YOLO_FALLBACK_MAX_MS / 1000.0)
        fallback_deadline = _min_deadline(deadline_at, fallback_stage_deadline)
        if OCR_MAX_FALLBACK_REGIONS > 0:
            regions = regions[:OCR_MAX_FALLBACK_REGIONS]
        if yolo_model is None and OCR_NO_YOLO_MAX_FALLBACK_REGIONS > 0:
            regions = regions[:OCR_NO_YOLO_MAX_FALLBACK_REGIONS]

        for region_name, region_img, offset in regions:
            if _is_deadline_reached(fallback_deadline):
                timeout_reached = True
                pipeline.append("deadline_reached:fallback_regions")
                break
            if (
                yolo_model is None
                and OCR_NO_YOLO_FALLBACK_MAX_MS > 0
                and ((perf_counter() - fallback_started) * 1000.0) >= OCR_NO_YOLO_FALLBACK_MAX_MS
            ):
                pipeline.append("fallback_budget_reached_no_yolo")
                break
            region_candidates = _ocr_scan(
                region_img,
                source=region_name,
                offset=offset,
                deadline_at=fallback_deadline,
                max_variants=OCR_NO_YOLO_FALLBACK_MAX_VARIANTS if yolo_model is None else None,
            )
            candidates.extend(region_candidates)
            if _has_strong_candidate(region_candidates):
                pipeline.append(f"fallback_short_circuit:{region_name}")
                break

        timings["fallback_ms"] = int(round((perf_counter() - fallback_started) * 1000))
        _emit(75, "fallback")

        # Ultima tentativa sem YOLO: regiões amplas com threshold mais permissivo.
        if not candidates and yolo_model is None and not _is_deadline_reached(deadline_at):
            last_started = perf_counter()
            pipeline.append("fallback_last_chance_no_yolo")
            last_stage_deadline = None
            if OCR_NO_YOLO_LAST_CHANCE_MAX_MS > 0:
                last_stage_deadline = last_started + (OCR_NO_YOLO_LAST_CHANCE_MAX_MS / 1000.0)
            last_deadline = _min_deadline(deadline_at, last_stage_deadline)
            c_x1 = proc_width // 4
            c_x2 = (proc_width * 3) // 4
            last_regions = [
                ("last_center_tall", np_img_rgb[:, c_x1:c_x2], (c_x1, 0)),
                ("last_bottom_half_center", np_img_rgb[proc_height // 2:proc_height, c_x1:c_x2], (c_x1, proc_height // 2)),
                ("last_top_half_center", np_img_rgb[0:proc_height // 2, c_x1:c_x2], (c_x1, 0)),
            ]
            for region_name, region_img, offset in last_regions:
                if _is_deadline_reached(last_deadline):
                    timeout_reached = True
                    pipeline.append("deadline_reached:last_chance_regions")
                    break
                if (
                    OCR_NO_YOLO_LAST_CHANCE_MAX_MS > 0
                    and ((perf_counter() - last_started) * 1000.0) >= OCR_NO_YOLO_LAST_CHANCE_MAX_MS
                ):
                    pipeline.append("last_chance_budget_reached_no_yolo")
                    break
                last_candidates = _ocr_scan(
                    region_img,
                    source=region_name,
                    offset=offset,
                    deadline_at=last_deadline,
                    max_variants=OCR_LAST_CHANCE_MAX_VARIANTS,
                    min_text_confidence=OCR_LAST_CHANCE_MIN_TEXT_CONFIDENCE,
                )
                candidates.extend(last_candidates)
                if _has_strong_candidate(last_candidates):
                    pipeline.append(f"last_chance_short_circuit:{region_name}")
                    break
            timings["fallback_last_chance_ms"] = int(round((perf_counter() - last_started) * 1000))
            _emit(83, "last_chance")

        # Se ainda não houver candidato e houver orçamento, roda um passe de resgate pesado.
        if not candidates and yolo_model is None and not _is_deadline_reached(deadline_at):
            if _remaining_deadline_ms(deadline_at) < OCR_NO_YOLO_RESCUE_MIN_REMAINING_MS:
                pipeline.append("rescue_skipped_low_budget")
            else:
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
                _emit(87, "rescue")
    elif not candidates and _is_deadline_reached(deadline_at):
        timeout_reached = True
        pipeline.append("deadline_reached:before_fallback")

    if _is_deadline_reached(deadline_at):
        timeout_reached = True

    deduped = _dedupe_candidates(
        candidates,
        proc_width,
        proc_height,
        limit=OCR_CANDIDATE_POOL_LIMIT,
    )
    deduped = _enforce_mercosul_scored_candidates(deduped)
    if candidates and not deduped:
        pipeline.append("mercosul_filter_empty")
    deduped, middle_letter_d_injected = _inject_middle_letter_d_from_o(deduped)
    if middle_letter_d_injected:
        pipeline.append("inject_middle_letter_d_from_o")
    deduped, last_digit_7_to_0_injected = _inject_last_digit_zero_from_seven(deduped)
    if last_digit_7_to_0_injected:
        pipeline.append("inject_last_digit_zero_from_seven")
    deduped, zero_priority_applied = _prioritize_zero_last_digit(deduped)
    if zero_priority_applied:
        pipeline.append("prioritize_zero_last_digit")
    deduped, mercosul_middle_priority_applied = _prioritize_mercosul_middle_letter(deduped)
    if mercosul_middle_priority_applied:
        pipeline.append("prioritize_mercosul_middle_letter")
    deduped, fourth_digit_priority_applied = _prioritize_fourth_digit_one_over_seven(deduped)
    if fourth_digit_priority_applied:
        pipeline.append("prioritize_fourth_digit_one_over_seven")
    deduped, fourth_digit_1_4_priority_applied = _prioritize_fourth_digit_four_over_one(deduped)
    if fourth_digit_1_4_priority_applied:
        pipeline.append("prioritize_fourth_digit_four_over_one")
    deduped, penultimate_digit_priority_applied = _prioritize_penultimate_digit_from_two(deduped)
    if penultimate_digit_priority_applied:
        pipeline.append("prioritize_penultimate_digit_from_two")
    deduped, penultimate_digit_0_9_priority_applied = _prioritize_penultimate_digit_nine_over_zero(deduped)
    if penultimate_digit_0_9_priority_applied:
        pipeline.append("prioritize_penultimate_digit_nine_over_zero")
    deduped, penultimate_digit_0_9_by_penalty_applied = _prioritize_penultimate_digit_by_penalty(deduped)
    if penultimate_digit_0_9_by_penalty_applied:
        pipeline.append("prioritize_penultimate_digit_0_9_by_penalty")
    deduped, middle_letter_d_over_o_priority_applied = _prioritize_middle_letter_d_over_o(deduped)
    if middle_letter_d_over_o_priority_applied:
        pipeline.append("prioritize_middle_letter_d_over_o")
    deduped, low_penalty_shell_priority_applied = _prioritize_lower_penalty_same_shell(deduped)
    if low_penalty_shell_priority_applied:
        pipeline.append("prioritize_lower_penalty_same_shell")
    deduped, prefix_y_over_v_priority_applied = _prioritize_prefix_y_over_v(deduped)
    if prefix_y_over_v_priority_applied:
        pipeline.append("prioritize_prefix_y_over_v")

    template_rerank_error = None
    template_rerank_info = None
    if deduped and not _is_deadline_reached(deadline_at):
        template_started = perf_counter()
        deduped, template_rerank_error, template_rerank_info = _apply_template_rerank(
            deduped,
            np_img_rgb,
            pipeline,
        )
        timings["template_rerank_ms"] = int(round((perf_counter() - template_started) * 1000))
        _emit(90, "rerank")

    # Reaplica prioridades apos rerank de template para evitar que o rerank
    # desfaça heuristicas de ambiguidade já calibradas em produção.
    deduped, last_digit_7_to_0_injected_post = _inject_last_digit_zero_from_seven(deduped)
    if last_digit_7_to_0_injected_post:
        pipeline.append("inject_last_digit_zero_from_seven_post_rerank")
    deduped, zero_priority_post_applied = _prioritize_zero_last_digit(deduped)
    if zero_priority_post_applied:
        pipeline.append("prioritize_zero_last_digit_post_rerank")
    deduped, mercosul_middle_priority_post_applied = _prioritize_mercosul_middle_letter(deduped)
    if mercosul_middle_priority_post_applied:
        pipeline.append("prioritize_mercosul_middle_letter_post_rerank")
    deduped, fourth_digit_priority_post_applied = _prioritize_fourth_digit_one_over_seven(deduped)
    if fourth_digit_priority_post_applied:
        pipeline.append("prioritize_fourth_digit_one_over_seven_post_rerank")
    deduped, fourth_digit_1_4_priority_post_applied = _prioritize_fourth_digit_four_over_one(deduped)
    if fourth_digit_1_4_priority_post_applied:
        pipeline.append("prioritize_fourth_digit_four_over_one_post_rerank")
    deduped, penultimate_digit_priority_post_applied = _prioritize_penultimate_digit_from_two(deduped)
    if penultimate_digit_priority_post_applied:
        pipeline.append("prioritize_penultimate_digit_from_two_post_rerank")
    deduped, penultimate_digit_0_9_priority_post_applied = _prioritize_penultimate_digit_nine_over_zero(deduped)
    if penultimate_digit_0_9_priority_post_applied:
        pipeline.append("prioritize_penultimate_digit_nine_over_zero_post_rerank")
    deduped, penultimate_digit_0_9_by_penalty_post_applied = _prioritize_penultimate_digit_by_penalty(deduped)
    if penultimate_digit_0_9_by_penalty_post_applied:
        pipeline.append("prioritize_penultimate_digit_0_9_by_penalty_post_rerank")
    deduped, middle_letter_d_over_o_priority_post_applied = _prioritize_middle_letter_d_over_o(deduped)
    if middle_letter_d_over_o_priority_post_applied:
        pipeline.append("prioritize_middle_letter_d_over_o_post_rerank")
    deduped, low_penalty_shell_priority_post_applied = _prioritize_lower_penalty_same_shell(deduped)
    if low_penalty_shell_priority_post_applied:
        pipeline.append("prioritize_lower_penalty_same_shell_post_rerank")
    deduped, prefix_y_over_v_priority_post_applied = _prioritize_prefix_y_over_v(deduped)
    if prefix_y_over_v_priority_post_applied:
        pipeline.append("prioritize_prefix_y_over_v_post_rerank")
    deduped, middle_letter_d_injected_post = _inject_middle_letter_d_from_o(deduped)
    if middle_letter_d_injected_post:
        pipeline.append("inject_middle_letter_d_from_o_post_rerank")

    if process_scale != 1.0:
        for candidate in deduped:
            candidate["bbox"] = _rescale_bbox(candidate.get("bbox"), process_scale, width, height)
    if OCR_RESPONSE_CANDIDATES_LIMIT > 0:
        deduped = deduped[:OCR_RESPONSE_CANDIDATES_LIMIT]
    ambiguous_top_pair = _is_ambiguous_top_pair(deduped)
    low_certainty = _is_low_certainty_best(deduped)
    if low_certainty:
        pipeline.append("low_certainty_best")
    requires_confirmation = ambiguous_top_pair or low_certainty
    best = None if requires_confirmation else (deduped[0] if deduped else None)
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
            "low_certainty": low_certainty,
            "requires_confirmation": requires_confirmation,
            "zero_priority_applied": zero_priority_applied,
            "mercosul_middle_priority_applied": mercosul_middle_priority_applied,
            "fourth_digit_priority_applied": fourth_digit_priority_applied,
            "fourth_digit_1_4_priority_applied": fourth_digit_1_4_priority_applied,
            "penultimate_digit_priority_applied": penultimate_digit_priority_applied,
            "penultimate_digit_0_9_priority_applied": penultimate_digit_0_9_priority_applied,
            "penultimate_digit_0_9_by_penalty_applied": penultimate_digit_0_9_by_penalty_applied,
            "middle_letter_d_over_o_priority_applied": middle_letter_d_over_o_priority_applied,
            "low_penalty_shell_priority_applied": low_penalty_shell_priority_applied,
            "middle_letter_d_injected": middle_letter_d_injected,
            "last_digit_7_to_0_injected": last_digit_7_to_0_injected,
            "prefix_y_over_v_priority_applied": prefix_y_over_v_priority_applied,
            "zero_priority_post_applied": zero_priority_post_applied,
            "mercosul_middle_priority_post_applied": mercosul_middle_priority_post_applied,
            "fourth_digit_priority_post_applied": fourth_digit_priority_post_applied,
            "fourth_digit_1_4_priority_post_applied": fourth_digit_1_4_priority_post_applied,
            "penultimate_digit_priority_post_applied": penultimate_digit_priority_post_applied,
            "penultimate_digit_0_9_priority_post_applied": penultimate_digit_0_9_priority_post_applied,
            "penultimate_digit_0_9_by_penalty_post_applied": penultimate_digit_0_9_by_penalty_post_applied,
            "middle_letter_d_over_o_priority_post_applied": middle_letter_d_over_o_priority_post_applied,
            "low_penalty_shell_priority_post_applied": low_penalty_shell_priority_post_applied,
            "middle_letter_d_injected_post": middle_letter_d_injected_post,
            "last_digit_7_to_0_injected_post": last_digit_7_to_0_injected_post,
            "prefix_y_over_v_priority_post_applied": prefix_y_over_v_priority_post_applied,
            "template_rerank": template_rerank_info,
            "template_rerank_error": template_rerank_error,
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


@app.route("/api/v1/plate/recognize-stream", methods=["POST"])
def recognize_plate_stream_for_nuxt():
    """
    SSE streaming do OCR de placa para o Nuxt.
    Emite eventos data: {progress, stage} e ao fim data: {progress:100, stage:'done', ok, result, input}.
    """
    data = request.get_json(silent=True) or {}
    base64_input = next(
        (data.get(f) for f in ("imageBase64", "image_base64", "base64", "image") if data.get(f)),
        None,
    )
    if not base64_input:
        def _err_gen():
            yield f"data: {json.dumps({'ok': False, 'error': 'imageBase64_required'})}\n\n"
        return Response(stream_with_context(_err_gen()), mimetype="text/event-stream"), 400

    filename = data.get("filename")
    request_id = data.get("requestId")

    q: Queue = Queue()

    def _run():
        try:
            img, input_meta = _decode_base64_image(base64_input)
            result = recognize_plate(
                img,
                progress_cb=lambda pct, stage: q.put(("progress", pct, stage)),
            )
            q.put(("done", result, input_meta))
        except ValueError as exc:
            q.put(("error", str(exc)))
        except Exception as exc:
            q.put(("error", str(exc)))

    thread = Thread(target=_run, daemon=True)
    thread.start()

    def _generate():
        while True:
            try:
                item = q.get(timeout=50)
            except Empty:
                yield f"data: {json.dumps({'ok': False, 'error': 'timeout'})}\n\n"
                break
            kind = item[0]
            if kind == "progress":
                _, pct, stage = item
                yield f"data: {json.dumps({'progress': pct, 'stage': stage})}\n\n"
            elif kind == "done":
                _, result, input_meta = item
                resp_input = dict(input_meta)
                if isinstance(filename, str) and filename.strip():
                    resp_input["filename"] = filename.strip()
                payload = {
                    "ok": True,
                    "progress": 100,
                    "stage": "done",
                    "input": resp_input,
                    "result": result,
                }
                if isinstance(request_id, str) and request_id.strip():
                    payload["requestId"] = request_id.strip()
                yield f"data: {json.dumps(payload)}\n\n"
                break
            elif kind == "error":
                _, msg = item
                yield f"data: {json.dumps({'ok': False, 'error': msg})}\n\n"
                break

    resp = Response(stream_with_context(_generate()), mimetype="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    return resp


def _maybe_preload_models():
    if not OCR_PRELOAD_MODELS:
        return
    get_yolo_model()
    get_ocr_reader()
    get_char_templates()


_maybe_preload_models()


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
