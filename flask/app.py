"""
Flask API - Picareta
"""
from flask import Flask, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)


@app.route('/', methods=['GET'])
def index():
    """Endpoint principal"""
    return jsonify({
        'message': 'Picareta Flask API',
        'status': 'ok',
        'version': '1.0.0'
    }), 200


if __name__ == '__main__':
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
