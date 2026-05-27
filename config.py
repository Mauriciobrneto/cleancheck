import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()


class Config:

    # ============================================================
    # CONFIGURAÇÕES GERAIS
    # ============================================================

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "cleancheck_secret_key"
    )

    # ============================================================
    # CONFIGURAÇÕES DO BANCO
    # ============================================================

    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_NAME = os.getenv("DB_NAME", "cleancheck")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://"
        f"{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ============================================================
    # CONFIGURAÇÕES FUTURAS
    # ============================================================

    # UPLOAD_FOLDER = "uploads"
    # MAX_CONTENT_LENGTH = 10 * 1024 * 1024