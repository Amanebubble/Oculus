from src.backend.database.db_manager import db
from src.backend.services.dte_service import DTEService
from src.backend.services.orchestrator import Orchestrator
from src.backend.utils.config import CARPETA_PROCESADOS

class Api:
    def __init__(self):
        self.dte_service = DTEService()
        self.orchestrator = Orchestrator()
    
    def get_stats(self):
        """Obtiene las estadísticas reales de la base de datos"""
        return db.get_stats()

    def start_processing(self):
        """Inicia el pipeline de procesamiento real (ahora con el Orquestador)"""
        print("Iniciando procesamiento...")
        self.orchestrator.start()
        return "Motor iniciado en segundo plano. Monitoreando cuentas..."
    
    def get_clients(self):
        if not CARPETA_PROCESADOS.exists(): return []
        return [f.name for f in CARPETA_PROCESADOS.iterdir() if f.is_dir()]
        
    def get_months(self, client_name):
        client_path = CARPETA_PROCESADOS / client_name
        if not client_path.exists(): return []
        return [f.name for f in client_path.iterdir() if f.is_dir()]
        
    def generate_excel(self, client_name, month_year, save_path):
        from src.backend.services.excel_service import ExcelService
        excel_service = ExcelService()
        client_path = CARPETA_PROCESADOS / client_name
        success, msg = excel_service.generar_libro_compras(client_path, month_year, save_path)
        return success, msg
        
    def choose_directory(self):
        import webview
        if webview.windows:
            window = webview.windows[0]
            result = window.create_file_dialog(webview.FOLDER_DIALOG)
            if result:
                return result[0]
        return None
        
    # --- EMAIL MANAGEMENT ---
    def get_emails(self):
        return db.get_all_emails()

    def add_email(self, client, email, password_enc, server, port=993):
        success, msg = db.add_email(email, password_enc, server, port)
        return success, msg
        
    # --- MANUAL REVIEW ---
    def get_manual_reviews(self):
        # Simulación de la base de datos de revisión
        # En producción esto vendría de CARPETA_REVISION
        return [
            {
                "id": 1,
                "pdf_path": str(CARPETA_PROCESADOS.parent / "04_Revision_Manual/doc_ilegible_1.pdf"),
                "uuid": "",
                "control": "",
                "date": "",
                "type": "03",
                "provider_name": "Procesado parcialmente",
                "provider_nit": ""
            }
        ]

    def save_manual_review(self, data):
        import json
        from pathlib import Path
        from src.backend.utils.config import CARPETA_DESCARGAS
        
        print(f"Revisión guardada: {data}")
        
        uuid = data.get("uuid", "UNKNOWN-UUID")
        
        # Build standard JSON based on the parsed data
        standard_json = {
            "identificacion": {
                "codigoGeneracion": uuid,
                "numeroControl": data.get("control", ""),
                "fecEmi": data.get("date", ""),
                "tipoDte": data.get("type", "03"),
            },
            "emisor": {
                "nombre": "Proveedor Desconocido" # En compra, el emisor es el proveedor
            },
            "receptor": {
                "nombre": data.get("provider_name", "Cliente_Manual")
            },
            "documentoRelacionado": [],
            "resumen": {
                "totalGravada": data.get("subtotal", 0),
                "subTotal": data.get("subtotal", 0),
                "tributos": [
                    {"codigo": "20", "descripcion": "Impuesto al Valor Agregado 13%", "valor": data.get("iva", 0)}
                ],
                "montoTotalOperacion": data.get("total", 0),
                "totalPagar": data.get("total", 0)
            },
            "selloRecepcion": {
                "selloRecepcion": data.get("sello", "")
            },
            "otros_impuestos_manuales": data.get("otros_impuestos", 0) # Campo custom para exportación
        }
        
        json_path = CARPETA_DESCARGAS / f"manual_{uuid}.json"
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(standard_json, f, indent=4)
            
        return True

    # --- GLOBAL CONTROLS ---
    def restart_service(self):
        print("Reiniciando motor...")
        self.orchestrator.stop()
        import time
        time.sleep(2)
        self.orchestrator.start()
        return True
        
    def shutdown_service(self):
        import webview
        print("Apagando aplicación...")
        self.orchestrator.stop()
        if webview.windows:
            webview.windows[0].destroy()
        return True
    
    def get_app_version(self):
        return "2.0.0"

    # --- SETTINGS ---
    def save_settings(self, data):
        import json
        from src.backend.utils.config import DATA_DIR
        settings_file = DATA_DIR / "settings.json"
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"Configuración de API guardada: {data}")
        return True
        
    def get_settings(self):
        import json
        from src.backend.utils.config import DATA_DIR
        settings_file = DATA_DIR / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
                
        return {
            "gemini": "",
            "llama": "",
            "groq": ""
        }

    # --- EXPLORER ---
    def get_other_documents(self, client_filter="", date_filter=""):
        # Dummy data for UI
        return [
            {
                "id": "file1",
                "name": "Factura_Rechazada_2026.pdf",
                "client": "Transporte Ejecutivo Shalom",
                "date": "2026-08-18",
                "type": "pdf",
                "path": "C:/dummy/Factura_Rechazada_2026.pdf"
            },
            {
                "id": "file2",
                "name": "JSON_No_DTE.json",
                "client": "Libreria Nacional",
                "date": "2026-08-17",
                "type": "json",
                "path": "C:/dummy/JSON_No_DTE.json"
            }
        ]
