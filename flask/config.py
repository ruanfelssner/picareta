"""
Configuração do serviço Flask
"""
import os
from typing import Optional


def get_env(key: str, default: Optional[str] = None) -> str:
    """Obtém variável de ambiente"""
    return os.environ.get(key, default)


# Configurações
CONFIG = {
    'FLASK_PORT': int(get_env('FLASK_PORT', '5000')),
    'FLASK_DEBUG': get_env('FLASK_DEBUG', 'False').lower() == 'true',
    'LOG_LEVEL': get_env('LOG_LEVEL', 'INFO'),
}
