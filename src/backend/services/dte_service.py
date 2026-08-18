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

    def _get_uid_from_filename(self, filename: str) -> str:
        """Extrae el UID del nombre de archivo. Formato: ALIAS_UID_FECHA_ORIGINAL"""
        partes = filename.split('_')
        if len(partes) >= 3:
            return f"{partes[0]}_{partes[1]}" # Devuelve ALIAS_UID como agrupador seguro
        return "UNKNOWN"

    def process_downloads(self):
        """
        Escanea la carpeta de descargas, empareja PDFs con JSONs usando el UID del correo 
        o procesa PDFs huérfanos mediante OCR/IA.
        """
        print("[*] Iniciando procesamiento matemático de descargas...")
        archivos = list(CARPETA_DESCARGAS.glob("*.*"))
        
        pdfs = [f for f in archivos if f.suffix.lower() == '.pdf']
        jsons = [f for f in archivos if f.suffix.lower() == '.json']
        
        resultados = {"procesados_json": 0, "procesados_ocr": 0, "otros": 0, "errores": 0}
        
        # Agrupar JSONs por ALIAS_UID
        jsons_por_uid = {}
        for j in jsons:
            uid = self._get_uid_from_filename(j.name)
            if uid not in jsons_por_uid:
                jsons_por_uid[uid] = []
            jsons_por_uid[uid].append(j)
            
        jsons_usados = set()

        for pdf in pdfs:
            pdf_emparejado = False
            json_asociado_data = None
            json_asociado_path = None
            
            uid = self._get_uid_from_filename(pdf.name)
            posibles_jsons = jsons_por_uid.get(uid, [])
            posibles_jsons = [j for j in posibles_jsons if j not in jsons_usados]
            
            # ESTRATEGIA 1: Emparejamiento por Nombre Base Exacto (El emisor los llamó igual)
            for j in posibles_jsons:
                if j.stem == pdf.stem:
                    json_asociado_path = j
                    json_asociado_data = self._leer_json(j)
                    jsons_usados.add(j)
                    pdf_emparejado = True
                    break
                    
            # ESTRATEGIA 2: Emparejamiento por UID (Si los llamaron distinto, pero solo hay 1 par en el correo)
            if not pdf_emparejado and len(posibles_jsons) == 1:
                # Ojo: Solo lo hacemos si es seguro (1 a 1). Si hay 2 PDFs y 2 JSONs revueltos, cae a OCR
                j = posibles_jsons[0]
                json_asociado_path = j
                json_asociado_data = self._leer_json(j)
                jsons_usados.add(j)
                pdf_emparejado = True
                print(f"[*] Emparejamiento heurístico: {pdf.name} <-> {j.name}")
                
            # ESTRATEGIA 3: Fallback a Inteligencia Artificial (Huérfano o Corrupto)
            if not pdf_emparejado:
                print(f"[*] Fallback a OCR para PDF huérfano: {pdf.name}")
                try:
                    raw_json = self.ocr.process_pdf_to_raw_json(str(pdf))
                    json_asociado_data = self.ocr.parse_raw_to_standard(raw_json)
                    
                    json_asociado_path = CARPETA_DESCARGAS / f"{pdf.stem}_standard.json"
                    with open(json_asociado_path, 'w', encoding='utf-8') as f:
                        json.dump(json_asociado_data, f, indent=4)
                        
                    resultados["procesados_ocr"] += 1
                except Exception as e:
                    db.log_extraction(pdf.name, "ERROR", error_msg=str(e))
                    resultados["errores"] += 1
                    continue
            else:
                resultados["procesados_json"] += 1

            # Filtrado por tipoDte (03, 05, 06, 14)
            if json_asociado_data:
                identificacion = json_asociado_data.get("identificacion", {})
                tipo_dte = str(identificacion.get("tipoDte", "")).zfill(2)
                
                # Rescate por si viene en el número de control (Fallback de seguridad)
                if not tipo_dte or tipo_dte == "00":
                    control = str(identificacion.get("numeroControl", "")).upper()
                    for t in self.target_codes:
                        if f"DTE-{t}" in control:
                            tipo_dte = t
                            break

                fecha = identificacion.get("fecEmi", "2000-01-01")
                mes_anio = fecha[:7] # YYYY-MM
                cliente = json_asociado_data.get("receptor", {}).get("nombre", "Cliente_Desconocido")
                
                cliente_folder = "".join(x for x in cliente if x.isalnum() or x in " -_").strip()
                subfolder = f"{cliente_folder}/{mes_anio}"

                archivos_a_mover = [pdf]
                if json_asociado_path and json_asociado_path.exists():
                    archivos_a_mover.append(json_asociado_path)

                if tipo_dte in self.target_codes:
                    self._mover_archivos(archivos_a_mover, CARPETA_PROCESADOS, subfolder)
                    db.log_extraction(pdf.name, "VALID_DTE", dte_code=tipo_dte)
                else:
                    self._mover_archivos(archivos_a_mover, CARPETA_OTROS_DTES, subfolder)
                    db.log_extraction(pdf.name, "OTHER_DTE", dte_code=tipo_dte)
                    resultados["otros"] += 1

        return resultados
