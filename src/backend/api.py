from src.backend.database.db_manager import db
from src.backend.services.dte_service import DTEService
from src.backend.utils.config import CARPETA_PROCESADOS

class Api:
    def __init__(self):
        self.dte_service = DTEService()
    
    def get_stats(self):
        """Obtiene las estadísticas reales de la base de datos"""
        return db.get_stats()

    def start_processing(self):
        """Inicia el pipeline de procesamiento real"""
        print("Iniciando procesamiento...")
        res = self.dte_service.process_downloads()
        return f"Finalizado: {res['procesados']} procesados, {res['otros']} archivados, {res['errores']} errores."
    
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

    def add_email(self, client, email, password_enc, server):
        success, msg = db.add_email(email, password_enc, server, 993)
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
        import time
        time.sleep(1) # Simular proceso de guardado y recatalogación
        print(f"Revisión guardada: {data}")
        return True

    # --- GLOBAL CONTROLS ---
    def restart_service(self):
        print("Reiniciando motor...")
        return True
        
    def shutdown_service(self):
        import webview
        print("Apagando aplicación...")
        if webview.windows:
            webview.windows[0].destroy()
        return True
    
    def get_app_version(self):
        return "2.0.0"

    # --- SETTINGS ---
    def save_settings(self, data):
        # Here we would save to sqlite or .env, for now just print
        print(f"Configuración de API guardada: {data}")
        return True
        
    def get_settings(self):
        # Return masked or empty values
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
