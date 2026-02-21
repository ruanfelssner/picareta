"""
Flask API - Picareta
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from PIL import Image

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "test"))
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}


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


def recognize_plate(img: Image.Image) -> dict:
    """
    Stub: aqui entra YOLO + OCR depois.
    Retorne o formato final desde já.
    """
    return {
        "plate": None,
        "confidence": 0.0,
        "bbox": None,
        "candidates": []
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


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)