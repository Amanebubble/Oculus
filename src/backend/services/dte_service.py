import os
import json
import shutil
from pathlib import Path
from src.backend.utils.config import CARPETA_DESCARGAS, CARPETA_PROCESADOS, CARPETA_OTROS_DTES
from src.backend.database.db_manager import db
from src.backend.services.ocr_service import OCRService

class DTEService:
    def __init__(self):
        self.ocr = OCRService()
        self.target_codes = ["03", "05", "06", "14"]

    def _leer_json(self, json_path: Path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def _mover_archivos(self, source_paths: list, dest_folder: Path, subfolder_name: str = None):
        """Mueve una lista de archivos a una carpeta destino, opcionalmente dentro de una subcarpeta (mes/año)"""
        target_dir = dest_folder / subfolder_name if subfolder_name else dest_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        
        for sp in source_paths:
            path = Path(sp)
            if path.exists():
                shutil.move(str(path), str(target_dir / path.name))

    def process_downloads(self):
        """
        Escanea la carpeta de descargas, empareja PDFs con JSONs mediante 'codigoGeneracion'
        o procesa PDFs sueltos mediante IA.
        """
        print("[*] Iniciando procesamiento de descargas...")
        archivos = list(CARPETA_DESCARGAS.glob("*.*"))
        
        # Separar PDFs y JSONs
        pdfs = [f for f in archivos if f.suffix.lower() == '.pdf']
        jsons = [f for f in archivos if f.suffix.lower() == '.json']
        
        # 1. Leer JSONs y armar un diccionario por codigoGeneracion
        diccionario_jsons = {}
        for j in jsons:
            data = self._leer_json(j)
            if data and "identificacion" in data and "codigoGeneracion" in data["identificacion"]:
                codigo = data["identificacion"]["codigoGeneracion"]
                diccionario_jsons[codigo] = {"path": j, "data": data}

        resultados = {"procesados": 0, "otros": 0, "errores": 0}

        # 2. Iterar sobre PDFs para intentar emparejar
        for pdf in pdfs:
            pdf_emparejado = False
            json_asociado_data = None
            json_asociado_path = None
            
            # TODO: Idealmente leer el código del PDF de alguna forma rápida (ej. PyMuPDF)
            # Para este ejemplo, asumimos que extraemos el código con OCR rápido:
            # (En producción, si el PDF viene con nombre "codigo_generacion.pdf", es directo)
            
            # Si no está emparejado por nombre/código rápido, usar la tubería Pesada:
            if not pdf_emparejado:
                try:
                    raw_json = self.ocr.process_pdf_to_raw_json(str(pdf))
                    json_asociado_data = self.ocr.parse_raw_to_standard(raw_json)
                    
                    # Generar un archivo JSON físico estándar para acompañar al PDF
                    json_asociado_path = CARPETA_DESCARGAS / f"{pdf.stem}_standard.json"
                    with open(json_asociado_path, 'w', encoding='utf-8') as f:
                        json.dump(json_asociado_data, f, indent=4)
                        
                except Exception as e:
                    db.log_extraction(pdf.name, "ERROR", error_msg=str(e))
                    resultados["errores"] += 1
                    continue

            # 3. Filtrado por tipoDte (03, 05, 06, 14)
            if json_asociado_data:
                tipo_dte = json_asociado_data.get("identificacion", {}).get("tipoDte", "")
                
                # Obtener info para agrupar (Mes y Año)
                fecha = json_asociado_data.get("identificacion", {}).get("fecEmi", "2000-01-01")
                mes_anio = fecha[:7] # YYYY-MM
                cliente = json_asociado_data.get("receptor", {}).get("nombre", "Cliente_Desconocido")
                
                # Sanitizar nombre de cliente para usar como carpeta
                cliente_folder = "".join(x for x in cliente if x.isalnum() or x in " -_").strip()
                subfolder = f"{cliente_folder}/{mes_anio}"

                archivos_a_mover = [pdf]
                if json_asociado_path and json_asociado_path.exists():
                    archivos_a_mover.append(json_asociado_path)

                if tipo_dte in self.target_codes:
                    # Es un código objetivo, va a procesados/cliente/mes
                    self._mover_archivos(archivos_a_mover, CARPETA_PROCESADOS, subfolder)
                    db.log_extraction(pdf.name, "VALID_DTE", dte_code=tipo_dte)
                    resultados["procesados"] += 1
                else:
                    # Otros DTEs
                    self._mover_archivos(archivos_a_mover, CARPETA_OTROS_DTES, subfolder)
                    db.log_extraction(pdf.name, "OTHER_DTE", dte_code=tipo_dte)
                    resultados["otros"] += 1

        return resultados
