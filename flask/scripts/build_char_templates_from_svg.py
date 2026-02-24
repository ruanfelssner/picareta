#!/usr/bin/env python3
"""
Gera templates de caracteres (A-Z, 0-9) a partir de um SVG de fonte.

Uso:
  python flask/scripts/build_char_templates_from_svg.py
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import cv2
import numpy as np

try:
    import cairosvg
except Exception as err:  # pragma: no cover
    cairosvg = None
    _CAIRO_ERR = str(err)
else:
    _CAIRO_ERR = None


DEFAULT_CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
DEFAULT_SVG = "public/fontes.svg"
DEFAULT_OUT = "flask/models/char_templates.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera templates de caracteres a partir de SVG.")
    parser.add_argument("--svg", default=DEFAULT_SVG, help=f"SVG de entrada (default: {DEFAULT_SVG})")
    parser.add_argument("--out", default=DEFAULT_OUT, help=f"JSON de saida (default: {DEFAULT_OUT})")
    parser.add_argument("--charset", default=DEFAULT_CHARSET, help="Sequencia de caracteres esperada.")
    parser.add_argument("--width", type=int, default=32, help="Largura do template final.")
    parser.add_argument("--height", type=int, default=48, help="Altura do template final.")
    parser.add_argument("--scale", type=float, default=2.8, help="Escala de rasterizacao do SVG.")
    parser.add_argument("--debug-preview", action="store_true", help="Salva preview com caixas/rotulos.")
    return parser.parse_args()


def render_svg_to_gray(svg_path: Path, scale: float) -> np.ndarray:
    if cairosvg is None:
        raise SystemExit(
            f"cairosvg indisponivel ({_CAIRO_ERR}). Rode: pip install cairosvg==2.7.1"
        )
    if not svg_path.is_file():
        raise SystemExit(f"SVG nao encontrado: {svg_path}")
    png_bytes = cairosvg.svg2png(url=str(svg_path), scale=max(0.5, float(scale)), background_color="white")
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None or img.size == 0:
        raise SystemExit("falha ao rasterizar SVG")
    return img


def find_glyph_boxes(gray: np.ndarray) -> List[Tuple[int, int, int, int, int]]:
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    found = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = found[0] if len(found) == 2 else found[1]

    h, w = bw.shape[:2]
    min_area = int(h * w * 0.00025)
    boxes: List[Tuple[int, int, int, int, int]] = []
    for contour in contours:
        x, y, cw, ch = cv2.boundingRect(contour)
        if cw <= 0 or ch <= 0:
            continue
        area = cw * ch
        if area < min_area:
            continue
        boxes.append((x, y, cw, ch, area))
    if not boxes:
        raise SystemExit("nenhum glifo detectado no SVG")
    return boxes


def sort_boxes_reading_order(boxes: Sequence[Tuple[int, int, int, int, int]]) -> List[Tuple[int, int, int, int, int]]:
    if not boxes:
        return []
    sorted_by_y = sorted(boxes, key=lambda item: (item[1] + item[3] // 2, item[0]))
    median_h = int(np.median([item[3] for item in sorted_by_y])) or 1
    row_tol = max(10, int(round(median_h * 0.75)))

    rows: List[Dict[str, object]] = []
    for box in sorted_by_y:
        x, y, cw, ch, area = box
        cy = y + (ch // 2)
        assigned = False
        for row in rows:
            row_cy = int(row["cy"])
            if abs(cy - row_cy) <= row_tol:
                row["boxes"].append(box)  # type: ignore[index]
                row["cy"] = int(round((row_cy + cy) / 2))
                assigned = True
                break
        if not assigned:
            rows.append({"cy": cy, "boxes": [box]})

    rows.sort(key=lambda item: int(item["cy"]))
    ordered: List[Tuple[int, int, int, int, int]] = []
    for row in rows:
        row_boxes = list(row["boxes"])  # type: ignore[arg-type]
        row_boxes.sort(key=lambda item: item[0])
        ordered.extend(row_boxes)
    return ordered


def normalize_binary(binary: np.ndarray, width: int, height: int) -> np.ndarray:
    ys, xs = np.where(binary > 0)
    if ys.size > 0 and xs.size > 0:
        y1, y2 = ys.min(), ys.max()
        x1, x2 = xs.min(), xs.max()
        cropped = binary[y1:y2 + 1, x1:x2 + 1]
    else:
        cropped = binary

    h, w = cropped.shape[:2]
    if h <= 0 or w <= 0:
        return np.zeros((height, width), dtype=np.uint8)

    scale = min(width / float(w), height / float(h))
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    resized = cv2.resize(cropped, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
    canvas = np.zeros((height, width), dtype=np.uint8)
    off_y = max(0, (height - new_h) // 2)
    off_x = max(0, (width - new_w) // 2)
    canvas[off_y:off_y + new_h, off_x:off_x + new_w] = (resized > 0).astype(np.uint8) * 255
    return canvas


def to_base64_png(image: np.ndarray) -> str:
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError("falha ao codificar template PNG")
    return base64.b64encode(encoded.tobytes()).decode("ascii")


def save_debug_preview(
    gray: np.ndarray,
    boxes: Sequence[Tuple[int, int, int, int, int]],
    labels: Sequence[str],
    out_path: Path,
) -> None:
    canvas = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    for idx, box in enumerate(boxes):
        x, y, cw, ch, _ = box
        label = labels[idx] if idx < len(labels) else str(idx)
        cv2.rectangle(canvas, (x, y), (x + cw, y + ch), (0, 180, 255), 2)
        cv2.putText(
            canvas,
            label,
            (x, max(12, y - 4)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
            cv2.LINE_AA,
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), canvas)


def main() -> None:
    args = parse_args()
    charset = "".join(ch for ch in (args.charset or "").upper() if ch.isalnum())
    if not charset:
        raise SystemExit("charset vazio")
    if args.width <= 0 or args.height <= 0:
        raise SystemExit("width/height devem ser > 0")

    svg_path = Path(args.svg).resolve()
    out_path = Path(args.out).resolve()

    gray = render_svg_to_gray(svg_path, scale=float(args.scale))
    boxes = find_glyph_boxes(gray)
    ordered = sort_boxes_reading_order(boxes)

    needed = len(charset)
    if len(ordered) < needed:
        raise SystemExit(
            f"glifos insuficientes no SVG ({len(ordered)}), esperado pelo menos {needed}"
        )

    selected = ordered[:needed]
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    templates: Dict[str, str] = {}
    for ch, box in zip(charset, selected):
        x, y, cw, ch_h, _ = box
        glyph = bw[y:y + ch_h, x:x + cw]
        normalized = normalize_binary(glyph, width=int(args.width), height=int(args.height))
        templates[ch] = to_base64_png(normalized)

    payload = {
        "version": 1,
        "source_svg": str(svg_path),
        "charset": charset,
        "template_size": {"width": int(args.width), "height": int(args.height)},
        "detected_glyphs": len(ordered),
        "used_glyphs": len(selected),
        "templates": templates,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    preview_path = out_path.with_suffix(".preview.png")
    if args.debug_preview:
        save_debug_preview(gray, selected, list(charset), preview_path)

    print(
        json.dumps(
            {
                "ok": True,
                "svg": str(svg_path),
                "out": str(out_path),
                "charset_len": len(charset),
                "detected_glyphs": len(ordered),
                "used_glyphs": len(selected),
                "preview": str(preview_path) if args.debug_preview else None,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
