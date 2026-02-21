#!/usr/bin/env python3
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
    import pytesseract  # type: ignore
except Exception as exc:  # pragma: no cover
    print(json.dumps({"error": "missing_dependencies", "details": str(exc)}))
    sys.exit(2)


LEGACY_PATTERN = re.compile(r"^[A-Z]{3}[0-9]{4}$")
MERCOSUL_PATTERN = re.compile(r"^[A-Z]{3}[0-9][A-Z][0-9]{2}$")

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
    "O": "0",
    "Q": "0",
    "D": "0",
    "I": "1",
    "L": "1",
    "Z": "2",
    "S": "5",
    "B": "8",
    "G": "6",
}

EXTRA_FOR_LETTER = {
    "0": [("O", 0.5), ("Q", 0.8), ("D", 0.95)],
    "1": [("I", 0.45), ("L", 0.6)],
    "2": [("Z", 0.6)],
    "4": [("A", 0.6)],
    "5": [("S", 0.55)],
    "6": [("G", 0.5), ("O", 0.95)],
    "7": [("T", 0.65)],
    "8": [("B", 0.55)],
    "T": [("O", 0.9), ("D", 1.05)],
    "Y": [("V", 0.9), ("D", 1.1)],
    "E": [("D", 0.95), ("F", 1.0)],
    "R": [("P", 0.95), ("B", 1.15)],
}

EXTRA_FOR_DIGIT = {
    "O": [("0", 0.35)],
    "Q": [("0", 0.45)],
    "D": [("0", 0.5)],
    "I": [("1", 0.35)],
    "L": [("1", 0.4)],
    "2": [("1", 1.1)],
    "7": [("1", 1.05)],
    "Z": [("2", 0.5)],
    "T": [("2", 0.9), ("7", 0.65)],
    "S": [("5", 0.5)],
    "B": [("8", 0.5)],
    "G": [("6", 0.5)],
    "A": [("4", 0.75)],
    "E": [("3", 0.75)],
    "Y": [("0", 1.0)],
}

WHITELIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
DEFAULT_LETTER_OPTIONS: List[Tuple[str, float]] = [("O", 1.6), ("D", 1.75), ("R", 1.85), ("A", 1.95), ("B", 2.05)]
DEFAULT_DIGIT_OPTIONS: List[Tuple[str, float]] = [("0", 1.35), ("1", 1.45), ("2", 1.55), ("7", 1.6), ("8", 1.72), ("5", 1.8)]


@dataclass
class Region:
    region_id: str
    image: np.ndarray
    weight: float


def resolve_tesseract_cmd() -> Optional[str]:
    found = shutil.which("tesseract")
    if found:
        return found

    if sys.platform.startswith("win"):
        user_home = os.path.expanduser("~")
        scoop_root = os.environ.get("SCOOP", "")
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
            r"C:\ProgramData\chocolatey\bin\tesseract.exe",
            r"C:\ProgramData\chocolatey\lib\tesseract\tools\tesseract.exe",
            os.path.join(user_home, "scoop", "apps", "tesseract", "current", "tesseract.exe"),
            os.path.join(scoop_root, "apps", "tesseract", "current", "tesseract.exe") if scoop_root else "",
        ]
        for path in candidates:
            if path and os.path.isfile(path):
                return path

    return None


def ensure_tesseract() -> Tuple[str, str]:
    command = resolve_tesseract_cmd()
    if not command:
        raise RuntimeError(
            "tesseract is not installed or it's not in your PATH. "
            "Install Tesseract OCR and restart the terminal."
        )

    pytesseract.pytesseract.tesseract_cmd = command

    try:
        version_proc = subprocess.run(
            [command, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=4,
        )
    except Exception as exc:
        raise RuntimeError(f"failed to execute tesseract binary: {exc}") from exc

    version_output = (version_proc.stdout or version_proc.stderr or "").strip().splitlines()
    version_line = version_output[0] if version_output else "unknown"

    if version_proc.returncode != 0:
        raise RuntimeError(f"tesseract binary failed to run: {version_line}")

    return command, version_line


def sanitize(value: str) -> str:
    return "".join(ch for ch in value.upper() if ("A" <= ch <= "Z") or ("0" <= ch <= "9"))


def normalize_legacy(candidate: str) -> Optional[str]:
    if len(candidate) != 7:
        return None
    normalized = (
        LETTER_FROM_DIGIT.get(candidate[0], candidate[0])
        + LETTER_FROM_DIGIT.get(candidate[1], candidate[1])
        + LETTER_FROM_DIGIT.get(candidate[2], candidate[2])
        + DIGIT_FROM_LETTER.get(candidate[3], candidate[3])
        + DIGIT_FROM_LETTER.get(candidate[4], candidate[4])
        + DIGIT_FROM_LETTER.get(candidate[5], candidate[5])
        + DIGIT_FROM_LETTER.get(candidate[6], candidate[6])
    )
    return normalized if LEGACY_PATTERN.match(normalized) else None


def normalize_mercosul(candidate: str) -> Optional[str]:
    if len(candidate) != 7:
        return None
    normalized = (
        LETTER_FROM_DIGIT.get(candidate[0], candidate[0])
        + LETTER_FROM_DIGIT.get(candidate[1], candidate[1])
        + LETTER_FROM_DIGIT.get(candidate[2], candidate[2])
        + DIGIT_FROM_LETTER.get(candidate[3], candidate[3])
        + LETTER_FROM_DIGIT.get(candidate[4], candidate[4])
        + DIGIT_FROM_LETTER.get(candidate[5], candidate[5])
        + DIGIT_FROM_LETTER.get(candidate[6], candidate[6])
    )
    return normalized if MERCOSUL_PATTERN.match(normalized) else None


def build_token_pool(text: str) -> List[str]:
    raw_tokens = [token for token in re.split(r"[^A-Z0-9]+", text.upper()) if token]
    pool: List[str] = []

    for token in raw_tokens:
        if len(token) >= 6:
            pool.append(token)

    for window in range(2, 7):
        for index in range(0, len(raw_tokens) - window + 1):
            chunk_tokens = raw_tokens[index:index + window]
            joined = "".join(chunk_tokens)
            if len(joined) < 6 or len(joined) > 16:
                continue
            if max(len(part) for part in chunk_tokens) > 4:
                continue
            pool.append(joined)

    compact = sanitize(text)
    if 6 <= len(compact) <= 24:
        pool.append(compact)

    return pool


def get_pattern_mask(pattern: str) -> List[str]:
    if pattern == "legacy":
        return ["L", "L", "L", "D", "D", "D", "D"]
    return ["L", "L", "L", "D", "L", "D", "D"]


def get_char_options(raw_char: str, expected: str) -> List[Tuple[str, float]]:
    options: Dict[str, float] = {}
    char = raw_char.upper()

    def push(candidate: str, cost: float) -> None:
        previous = options.get(candidate)
        if previous is None or cost < previous:
            options[candidate] = cost

    if expected == "L":
        if "A" <= char <= "Z":
            push(char, 0.0)
        mapped = LETTER_FROM_DIGIT.get(char)
        if mapped:
            push(mapped, 0.45)
        for candidate, cost in EXTRA_FOR_LETTER.get(char, []):
            push(candidate, cost)
    else:
        if "0" <= char <= "9":
            push(char, 0.0)
        mapped = DIGIT_FROM_LETTER.get(char)
        if mapped:
            push(mapped, 0.4)
        for candidate, cost in EXTRA_FOR_DIGIT.get(char, []):
            push(candidate, cost)

    return sorted(options.items(), key=lambda item: item[1])


def decode_window(window: str, pattern: str, beam_width: int = 10, max_cost: float = 3.4) -> List[Tuple[str, float]]:
    mask = get_pattern_mask(pattern)
    if len(window) != len(mask):
        return []

    beam: List[Tuple[str, float]] = [("", 0.0)]
    for index, expected in enumerate(mask):
        options = get_char_options(window[index], expected)
        if not options:
            return []

        next_map: Dict[str, float] = {}
        for partial, partial_cost in beam:
            for candidate, candidate_cost in options[:5]:
                merged = partial + candidate
                cost = partial_cost + candidate_cost
                if cost > max_cost:
                    continue
                previous = next_map.get(merged)
                if previous is None or cost < previous:
                    next_map[merged] = cost

        beam = sorted(next_map.items(), key=lambda item: item[1])[:beam_width]
        if not beam:
            return []

    regex = LEGACY_PATTERN if pattern == "legacy" else MERCOSUL_PATTERN
    return [(candidate, cost) for candidate, cost in beam if regex.match(candidate)]


def clamp_confidence(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 100:
        return 100.0
    return float(value)


def decode_char_cells(
    raw_chars: List[str],
    confidences: List[float],
    pattern: str,
    beam_width: int = 10,
    max_cost: float = 4.9,
) -> List[Tuple[str, float]]:
    mask = get_pattern_mask(pattern)
    if len(raw_chars) != len(mask):
        return []

    beam: List[Tuple[str, float]] = [("", 0.0)]
    for index, expected in enumerate(mask):
        char = sanitize(str(raw_chars[index] or ""))[:1]
        confidence = clamp_confidence(float(confidences[index] if index < len(confidences) else 0.0))

        options = get_char_options(char, expected)[:6] if char else []
        if not options:
            options = DEFAULT_LETTER_OPTIONS if expected == "L" else DEFAULT_DIGIT_OPTIONS

        confidence_penalty = max(0.0, 58.0 - confidence) * 0.0105

        next_map: Dict[str, float] = {}
        for partial, partial_cost in beam:
            for candidate, candidate_cost in options:
                substitution_penalty = 0.0 if char and candidate == char else 0.03
                merged = partial + candidate
                cost = partial_cost + candidate_cost + confidence_penalty + substitution_penalty
                if cost > max_cost:
                    continue
                previous = next_map.get(merged)
                if previous is None or cost < previous:
                    next_map[merged] = cost

        beam = sorted(next_map.items(), key=lambda item: item[1])[:beam_width]
        if not beam:
            return []

    regex = LEGACY_PATTERN if pattern == "legacy" else MERCOSUL_PATTERN
    return [(candidate, cost) for candidate, cost in beam if regex.match(candidate)]


def extract_char_cell_candidates(
    region: Region,
    started: float,
    max_runtime_seconds: float,
) -> Tuple[List[Tuple[str, float]], List[str]]:
    traces: List[str] = []
    h, w = region.image.shape[:2]
    if w < 150 or h < 24:
        return [], traces

    ratio = w / float(max(1, h))
    if ratio < 2.15 or ratio > 7.4:
        return [], traces

    gray = cv2.cvtColor(region.image, cv2.COLOR_BGR2GRAY)
    target_w = max(320, min(1200, w * 2))
    target_h = max(72, int(target_w * (h / float(max(1, w)))))
    resized = cv2.resize(gray, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
    normal = cv2.equalizeHist(resized)
    blur = cv2.GaussianBlur(normal, (5, 5), 0)
    otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    inverted = cv2.bitwise_not(otsu)

    variants = [("otsu", otsu, 1.08), ("inv", inverted, 1.0)]
    all_candidates: Dict[str, float] = {}

    for variant_name, variant_img, variant_weight in variants:
        if time.monotonic() - started > max_runtime_seconds:
            traces.append("[budget] char-cell OCR interrupted.")
            break

        vh, vw = variant_img.shape[:2]
        left_margin = int(vw * 0.08)
        right_margin = int(vw * 0.08)
        top_margin = int(vh * 0.16)
        bottom_margin = int(vh * 0.18)
        inner_w = max(1, vw - left_margin - right_margin)
        inner_h = max(1, vh - top_margin - bottom_margin)
        cell_w = inner_w / 7.0

        raw_chars: List[str] = []
        confidences: List[float] = []
        recognized = 0

        for index in range(7):
            if time.monotonic() - started > max_runtime_seconds:
                break

            x = int(left_margin + index * cell_w + cell_w * 0.08)
            cw = max(10, int(cell_w * 0.84))
            y = max(0, top_margin)
            ch = max(12, inner_h)
            x = max(0, min(vw - 1, x))
            cw = max(1, min(vw - x, cw))

            crop = variant_img[y:y + ch, x:x + cw]
            if crop.size == 0:
                raw_chars.append("")
                confidences.append(0.0)
                continue

            config = f"--oem 1 --psm 10 -c tessedit_char_whitelist={WHITELIST}"
            best_char = sanitize(pytesseract.image_to_string(crop, config=config))[:1]
            best_conf = 46.0 if best_char else 0.0

            if not best_char:
                retry = sanitize(pytesseract.image_to_string(cv2.bitwise_not(crop), config=config))[:1]
                if retry:
                    best_char = retry
                    best_conf = 34.0

            raw_chars.append(best_char)
            confidences.append(best_conf)
            if best_char:
                recognized += 1

        if recognized < 3:
            continue

        raw_text = "".join(char if char else "?" for char in raw_chars)
        avg_conf = sum(confidences) / max(1, len(confidences))
        traces.append(f"[{region.region_id}-cells-{variant_name}] {raw_text} ({avg_conf:.1f})")

        decoded = decode_char_cells(raw_chars, confidences, "mercosul")[:6] + decode_char_cells(raw_chars, confidences, "legacy")[:4]
        for candidate, cost in decoded:
            score = max(0.0, (avg_conf / 100.0) * variant_weight * region.weight / (1.0 + cost))
            previous = all_candidates.get(candidate)
            if previous is None or score > previous:
                all_candidates[candidate] = score

    rows = sorted(all_candidates.items(), key=lambda item: item[1], reverse=True)
    return rows[:10], traces


def extract_plate_candidates(text: str) -> List[Tuple[str, float, bool]]:
    pool = build_token_pool(text)
    best: Dict[str, Tuple[float, bool]] = {}

    def push(candidate: Optional[str], cost: float, strict: bool) -> None:
        if not candidate:
            return
        current = best.get(candidate)
        if current is None or cost < current[0]:
            best[candidate] = (cost, strict)
        elif strict and not current[1]:
            best[candidate] = (current[0], True)

    for token in pool:
        compact = sanitize(token)
        if len(compact) < 7:
            continue

        for start in range(0, min(len(compact) - 6, 18)):
            window = compact[start:start + 7]
            push(normalize_legacy(window), 0.0, True)
            push(normalize_mercosul(window), 0.0, True)

            for candidate, cost in decode_window(window, "legacy"):
                push(candidate, cost, False)
            for candidate, cost in decode_window(window, "mercosul"):
                push(candidate, cost, False)

    rows = [(candidate, values[0], values[1]) for candidate, values in best.items()]
    rows.sort(key=lambda item: (0 if item[2] else 1, item[1], item[0]))
    return rows[:18]


def decode_image(base64_data: str) -> np.ndarray:
    payload = base64_data.split(",", 1)[1] if "," in base64_data else base64_data
    binary = base64.b64decode(payload)
    arr = np.frombuffer(binary, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("invalid_image")

    height, width = image.shape[:2]
    if width == 0 or height == 0:
        raise ValueError("invalid_dimensions")

    if width < 900:
        scale = 900.0 / width
        image = cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_CUBIC)
    elif width > 2200:
        scale = 2200.0 / width
        image = cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)

    return image


def clamp_box(box: Tuple[int, int, int, int], width: int, height: int) -> Optional[Tuple[int, int, int, int]]:
    x, y, w, h = box
    x = max(0, min(width - 1, x))
    y = max(0, min(height - 1, y))
    w = max(1, min(width - x, w))
    h = max(1, min(height - y, h))
    if w < 80 or h < 20:
        return None
    return (x, y, w, h)


def propose_regions(image: np.ndarray) -> List[Region]:
    height, width = image.shape[:2]
    proposals: List[Tuple[str, Tuple[int, int, int, int], float]] = []

    fixed = [
        ("center-wide", (int(width * 0.16), int(height * 0.54), int(width * 0.68), int(height * 0.30)), 1.55),
        ("center-narrow", (int(width * 0.24), int(height * 0.60), int(width * 0.52), int(height * 0.22)), 1.70),
        ("lower-half", (int(width * 0.08), int(height * 0.50), int(width * 0.84), int(height * 0.45)), 1.20),
    ]
    proposals.extend(fixed)

    for y_ratio in [0.54, 0.62, 0.70]:
        for x_ratio in [0.34, 0.50, 0.66]:
            for w_ratio in [0.24, 0.30, 0.36]:
                box_w = int(width * w_ratio)
                box_h = max(32, int(min(height * 0.18, box_w / 3.2)))
                x = int(width * x_ratio - box_w / 2)
                y = int(height * y_ratio - box_h / 2)
                proposals.append((f"strip-{int(x_ratio*100)}-{int(y_ratio*100)}-{int(w_ratio*100)}", (x, y, box_w, box_h), 1.42))

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.bilateralFilter(gray, 11, 17, 17)
    edges = cv2.Canny(denoised, 35, 200)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)[:70]

    for index, contour in enumerate(sorted_contours):
        x, y, w, h = cv2.boundingRect(contour)
        if w < 120 or h < 24:
            continue
        ratio = w / float(max(1, h))
        if ratio < 2.1 or ratio > 7.4:
            continue

        area = w * h
        min_area = max(3500, int((width * height) * 0.003))
        if area < min_area:
            continue

        perimeter = cv2.arcLength(contour, True)
        if perimeter <= 0:
            continue
        approx = cv2.approxPolyDP(contour, 0.03 * perimeter, True)
        points = len(approx)
        if points < 4 or points > 9:
            continue

        center_x = (x + w / 2.0) / width
        center_y = (y + h / 2.0) / height
        position_bonus = 1.28 - min(0.46, abs(center_x - 0.5) * 0.95 + max(0.0, 0.58 - center_y) * 0.85)
        shape_bonus = 1.24 if 4 <= points <= 6 else 1.12
        proposals.append((f"contour-{index}", (x, y, w, h), max(0.76, position_bonus * shape_bonus)))

    dedup: Dict[Tuple[int, int, int, int], Tuple[str, Tuple[int, int, int, int], float]] = {}
    for region_id, raw_box, weight in proposals:
        box = clamp_box(raw_box, width, height)
        if not box:
            continue

        key = (
            round(box[0] / 24),
            round(box[1] / 20),
            round(box[2] / 24),
            round(box[3] / 20),
        )
        current = dedup.get(key)
        if current is None or weight > current[2]:
            dedup[key] = (region_id, box, weight)

    result: List[Region] = []
    for region_id, (x, y, w, h), weight in dedup.values():
        crop = image[y:y + h, x:x + w]
        if crop.size == 0:
            continue
        result.append(Region(region_id=region_id, image=crop, weight=weight))

    result.sort(key=lambda item: item.weight, reverse=True)
    return result[:22]


def preprocess_region(region: np.ndarray) -> List[Tuple[str, np.ndarray, float]]:
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    target_w = max(280, min(1400, w * 2))
    target_h = max(64, int(target_w * (h / float(max(1, w)))))
    resized = cv2.resize(gray, (target_w, target_h), interpolation=cv2.INTER_CUBIC)

    normal = cv2.equalizeHist(resized)
    blur = cv2.GaussianBlur(normal, (5, 5), 0)
    otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return [
        ("normal", normal, 1.0),
        ("otsu", otsu, 1.08),
    ]


def ocr_entries(region: Region) -> List[Tuple[str, float, float, str]]:
    entries: List[Tuple[str, float, float, str]] = []
    modes = [
        ("psm7", 7, 1.0),
    ]

    for variant_name, variant_img, variant_weight in preprocess_region(region.image):
        for mode_name, psm, psm_weight in modes:
            config = f"--oem 1 --psm {psm} -c tessedit_char_whitelist={WHITELIST}"
            data = pytesseract.image_to_data(variant_img, config=config, output_type=pytesseract.Output.DICT)

            words: List[str] = []
            confidences: List[float] = []
            for idx, text in enumerate(data.get("text", [])):
                word = sanitize(str(text or ""))
                if not word:
                    continue
                conf_raw = str(data.get("conf", ["-1"])[idx] or "-1")
                try:
                    conf = float(conf_raw)
                except Exception:
                    conf = -1.0
                if conf < 0:
                    continue
                words.append(word)
                confidences.append(conf)

            if not words:
                line = sanitize(pytesseract.image_to_string(variant_img, config=config))
                if len(line) >= 6:
                    entries.append((line, 24.0, variant_weight * psm_weight * 0.55, f"{region.region_id}-{variant_name}-{mode_name}-line"))
                continue

            text = " ".join(words)
            confidence = sum(confidences) / len(confidences)
            weight = variant_weight * psm_weight
            entries.append((text, confidence, weight, f"{region.region_id}-{variant_name}-{mode_name}"))

    return entries


def detect_plate(image: np.ndarray) -> Dict[str, object]:
    regions = propose_regions(image)
    candidate_scores: Dict[str, float] = {}
    candidate_hits: Dict[str, int] = {}
    traces: List[str] = []
    started = time.monotonic()
    max_runtime_seconds = 20.0

    for region_index, region in enumerate(regions):
        if time.monotonic() - started > max_runtime_seconds:
            traces.append("[budget] OCR budget exceeded; returning partial result.")
            break

        region_scores: Dict[str, float] = {}

        should_run_cells = region_index < 12 and region.weight >= 1.0
        if should_run_cells and time.monotonic() - started <= max_runtime_seconds:
            cell_candidates, cell_traces = extract_char_cell_candidates(region, started, max_runtime_seconds)
            for trace in cell_traces:
                if len(traces) < 260:
                    traces.append(trace)

            for candidate, score in cell_candidates:
                delta = score * 2.35
                region_scores[candidate] = region_scores.get(candidate, 0.0) + delta

        should_run_line_ocr = (
            (len(candidate_scores) == 0 or region_index < 6) and
            region_index < 14 and
            time.monotonic() - started <= max_runtime_seconds
        )
        if should_run_line_ocr:
            entries = ocr_entries(region)
            for text, confidence, entry_weight, trace_id in entries:
                if time.monotonic() - started > max_runtime_seconds:
                    traces.append("[budget] OCR budget exceeded during region parse.")
                    break

                if len(traces) < 260:
                    traces.append(f"[{trace_id}] {text} ({confidence:.1f})")

                extracted = extract_plate_candidates(text)
                if not extracted:
                    continue

                confidence_factor = max(0.25, min(1.25, confidence / 70.0))
                for candidate, cost, strict in extracted:
                    strict_bonus = 1.12 if strict else 0.62
                    delta = entry_weight * region.weight * confidence_factor * strict_bonus * 2.8 / (1.0 + cost)
                    region_scores[candidate] = region_scores.get(candidate, 0.0) + delta

        for candidate, score in region_scores.items():
            clamped = min(score, region.weight * 3.8)
            candidate_scores[candidate] = candidate_scores.get(candidate, 0.0) + clamped
            candidate_hits[candidate] = candidate_hits.get(candidate, 0) + 1

        ranked_now = sorted(
            candidate_scores.items(),
            key=lambda item: (item[1] + candidate_hits.get(item[0], 0) * 0.16),
            reverse=True,
        )
        if len(ranked_now) >= 2:
            best = ranked_now[0][1]
            second = ranked_now[1][1]
            if best >= 3.4 and (best - second) >= 0.95:
                traces.append("[early-stop] confident candidate reached.")
                break

    ranked = sorted(
        candidate_scores.items(),
        key=lambda item: (item[1] + candidate_hits.get(item[0], 0) * 0.16),
        reverse=True,
    )

    candidates = [item[0] for item in ranked[:12]]
    best_score = ranked[0][1] if ranked else 0.0
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0

    return {
        "plate": candidates[0] if candidates else "",
        "candidates": candidates,
        "bestScore": round(float(best_score), 6),
        "secondScore": round(float(second_score), 6),
        "rawText": "\n".join(traces),
    }


def run_check() -> int:
    try:
        command, version = ensure_tesseract()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "tesseract_unavailable",
                    "details": str(exc),
                    "deps": {
                        "python": sys.version.split(" ")[0],
                        "opencv": getattr(cv2, "__version__", "unknown"),
                        "numpy": getattr(np, "__version__", "unknown"),
                        "pytesseract": getattr(pytesseract, "__version__", "unknown"),
                    },
                }
            )
        )
        return 1

    info = {
        "python": sys.version.split(" ")[0],
        "opencv": getattr(cv2, "__version__", "unknown"),
        "numpy": getattr(np, "__version__", "unknown"),
        "pytesseract": getattr(pytesseract, "__version__", "unknown"),
        "tesseract_cmd": command,
        "tesseract_version": version,
    }
    print(json.dumps({"ok": True, "deps": info}))
    return 0


def main() -> int:
    if "--check" in sys.argv:
        return run_check()

    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps({"error": "empty_payload"}))
        return 1

    try:
        payload = json.loads(raw)
    except Exception:
        print(json.dumps({"error": "invalid_json"}))
        return 1

    image_base64 = str(payload.get("imageBase64", "")).strip()
    if not image_base64:
        print(json.dumps({"error": "missing_image"}))
        return 1

    try:
        ensure_tesseract()
        image = decode_image(image_base64)
        result = detect_plate(image)
        print(json.dumps(result))
        return 0
    except Exception as exc:
        print(json.dumps({"error": "ocr_failed", "details": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
