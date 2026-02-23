#!/usr/bin/env python3
"""
Exporta dataset treinavel a partir da colecao `ocr_feedback_events`.

Uso sugerido (rodar 1x por dia via cron):
  python flask/scripts/export_ocr_feedback_dataset.py --days 1
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

from pymongo import MongoClient


DEFAULT_COLLECTION = "ocr_feedback_events"
DEFAULT_OUT_DIR = "data/datasets/ocr-feedback"
MIME_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@dataclass
class Config:
    mongo_uri: str
    db_name: str
    collection: str
    out_dir: Path
    days: int
    only_corrected: bool
    with_base64: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exporta dataset de feedback OCR da placa.")
    parser.add_argument("--mongo-uri", default=os.getenv("MONGODB_URI") or os.getenv("NUXT_MONGO_URI"))
    parser.add_argument("--db-name", default=os.getenv("NUXT_MONGO_DB_NAME"))
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument(
        "--only-corrected",
        action="store_true",
        help="Exporta somente eventos corrigidos (por padrao exporta todo feedback util).",
    )
    parser.add_argument(
        "--with-base64",
        action="store_true",
        help="Inclui crop base64 no JSONL exportado (aumenta muito o tamanho).",
    )
    return parser.parse_args()


def resolve_db_name(explicit: Optional[str], mongo_uri: str) -> Optional[str]:
    if explicit:
        return explicit
    parsed = urlparse(mongo_uri)
    if not parsed.path:
        return None
    name = parsed.path.lstrip("/")
    return name or None


def build_config(args: argparse.Namespace) -> Config:
    if not args.mongo_uri:
        raise SystemExit("Mongo URI ausente. Use --mongo-uri ou configure MONGODB_URI/NUXT_MONGO_URI.")

    db_name = resolve_db_name(args.db_name, args.mongo_uri)
    if not db_name:
        raise SystemExit("Nome do banco ausente. Use --db-name ou configure NUXT_MONGO_DB_NAME.")

    days = max(1, int(args.days))
    out_dir = Path(args.out_dir).resolve()

    return Config(
        mongo_uri=args.mongo_uri,
        db_name=db_name,
        collection=args.collection,
        out_dir=out_dir,
        days=days,
        only_corrected=bool(args.only_corrected),
        with_base64=bool(args.with_base64),
    )


def parse_data_url(data_url: str) -> Optional[Tuple[str, bytes]]:
    if not data_url or not isinstance(data_url, str):
        return None
    if not data_url.startswith("data:image/") or "," not in data_url:
        return None

    header, encoded = data_url.split(",", 1)
    if ";base64" not in header:
        return None

    mime = header.split(";", 1)[0].replace("data:", "").strip().lower()
    if mime not in MIME_EXT:
        return None

    try:
        content = base64.b64decode(encoded, validate=True)
    except Exception:
        return None

    if not content:
        return None

    return mime, content


def to_serializable(record: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in record.items():
        if key == "_id":
            out["id"] = str(value)
        else:
            out[key] = value
    return out


def main() -> None:
    args = parse_args()
    config = build_config(args)

    config.out_dir.mkdir(parents=True, exist_ok=True)
    crops_dir = config.out_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=config.days)
    since_iso = since.isoformat()

    query: Dict[str, Any] = {
        "createdAt": {"$gte": since_iso},
        "$or": [
            {"usefulReason": {"$in": ["corrected", "ambiguous", "missing_recognition"]}},
            {"usefulReason": {"$exists": False}, "corrected": True},
        ],
    }
    if config.only_corrected:
        query["corrected"] = True

    client = MongoClient(config.mongo_uri)
    collection = client[config.db_name][config.collection]
    rows = list(collection.find(query).sort("createdAt", 1))

    export_tag = now.strftime("%Y%m%dT%H%M%SZ")
    jsonl_path = config.out_dir / f"ocr_feedback_dataset_{export_tag}.jsonl"
    csv_path = config.out_dir / f"ocr_feedback_manifest_{export_tag}.csv"

    exported = 0
    with_crops = 0

    with jsonl_path.open("w", encoding="utf-8") as jsonl_file, csv_path.open(
        "w", encoding="utf-8", newline=""
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "id",
                "createdAt",
                "requestId",
                "source",
                "usefulReason",
                "recognizedPlate",
                "confirmedPlate",
                "corrected",
                "candidates",
                "bbox",
                "imageWidth",
                "imageHeight",
                "cropPath",
                "cropBytes",
            ],
        )
        writer.writeheader()

        for raw in rows:
            row = to_serializable(raw)
            crop_data_url = str(row.get("plateCropBase64") or "")
            crop_path = ""
            crop_bytes = 0

            parsed_crop = parse_data_url(crop_data_url)
            if parsed_crop:
                mime, content = parsed_crop
                ext = MIME_EXT.get(mime, ".jpg")
                crop_path = str((crops_dir / f"{row['id']}{ext}").resolve())
                Path(crop_path).write_bytes(content)
                crop_bytes = len(content)
                with_crops += 1

            dataset_line = {
                "id": row.get("id"),
                "createdAt": row.get("createdAt"),
                "requestId": row.get("requestId"),
                "source": row.get("source"),
                "usefulReason": row.get("usefulReason"),
                "recognizedPlate": row.get("recognizedPlate"),
                "confirmedPlate": row.get("confirmedPlate"),
                "corrected": bool(row.get("corrected")),
                "candidates": row.get("candidates") or [],
                "diffPositions": row.get("diffPositions") or [],
                "bbox": row.get("bbox"),
                "imageSize": row.get("imageSize"),
                "cropPath": crop_path or None,
                "timingsMs": row.get("timingsMs") or {},
            }
            if config.with_base64 and crop_data_url:
                dataset_line["plateCropBase64"] = crop_data_url

            jsonl_file.write(json.dumps(dataset_line, ensure_ascii=False) + "\n")

            image_size = row.get("imageSize") or {}
            writer.writerow(
                {
                    "id": row.get("id"),
                    "createdAt": row.get("createdAt"),
                    "requestId": row.get("requestId"),
                    "source": row.get("source"),
                    "usefulReason": row.get("usefulReason"),
                    "recognizedPlate": row.get("recognizedPlate"),
                    "confirmedPlate": row.get("confirmedPlate"),
                    "corrected": bool(row.get("corrected")),
                    "candidates": "|".join(row.get("candidates") or []),
                    "bbox": json.dumps(row.get("bbox"), ensure_ascii=False),
                    "imageWidth": image_size.get("width"),
                    "imageHeight": image_size.get("height"),
                    "cropPath": crop_path,
                    "cropBytes": crop_bytes,
                }
            )
            exported += 1

    print(
        json.dumps(
            {
                "ok": True,
                "mongo_db": config.db_name,
                "collection": config.collection,
                "window_days": config.days,
                "only_corrected": config.only_corrected,
                "rows": exported,
                "rows_with_crops": with_crops,
                "jsonl": str(jsonl_path),
                "csv": str(csv_path),
                "crops_dir": str(crops_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
