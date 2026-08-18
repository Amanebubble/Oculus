import os
import sys
from pathlib import Path

def get_base_dir() -> Path:
    """
    Retorna la ruta base absoluta del proyecto, resolviendo si se está 
    ejecutando como un ejecutable compilado por PyInstaller o como script normal.
    """
    if getattr(sys, 'frozen', False):
        # Si se ejecuta como .exe empaquetado (PyInstaller)
        return Path(sys.executable).parent
    else:
        # Si se ejecuta como script Python (.py)
        return Path(__file__).resolve().parent.parent.parent.parent

BASE_DIR = get_base_dir()
SRC_DIR = BASE_DIR / "src"
FRONTEND_DIR = SRC_DIR / "frontend"
BACKEND_DIR = SRC_DIR / "backend"

# Carpetas de datos
DATA_DIR = BASE_DIR / "data"
CARPETA_DESCARGAS = DATA_DIR / "01_Descargas"
CARPETA_PROCESADOS = DATA_DIR / "02_Procesados"
CARPETA_OTROS_DTES = DATA_DIR / "03_Otros_DTEs"
CARPETA_REVISION = DATA_DIR / "04_Revision_Manual"
CARPETA_BD = DATA_DIR / "db"

# Asegurar que las carpetas existan
def init_directories():
    directories = [
        DATA_DIR, CARPETA_DESCARGAS, CARPETA_PROCESADOS, 
        CARPETA_OTROS_DTES, CARPETA_REVISION, CARPETA_BD
    ]
    for d in directories:
        d.mkdir(parents=True, exist_ok=True)

init_directories()

DB_PATH = CARPETA_BD / "oculus.db"
