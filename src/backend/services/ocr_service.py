import os
import json
import fitz  # PyMuPDF
from groq import Groq
from pathlib import Path

class OCRService:
    def __init__(self):
        # En el futuro, estas llaves se leerán desde la BD o el archivo de configuración local
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.groq_client = Groq(api_key=self.groq_api_key) if self.groq_api_key else None

    def _extract_local_text(self, pdf_path: str) -> str:
        """Extrae el texto del PDF localmente usando PyMuPDF (Costo $0)"""
        try:
            doc = fitz.open(pdf_path)
            texto = ""
            for page in doc:
                texto += page.get_text() + "\n"
            return texto.strip()
        except Exception as e:
            print(f"Error extrayendo texto de {pdf_path}: {e}")
            return ""

    def process_pdf_to_raw_json(self, pdf_path: str) -> dict:
        """
        Tubería principal: PyMuPDF -> Groq (Llama 3.1 8B) -> JSON Crudo
        """
        print(f"[*] Iniciando Extracción Híbrida (PyMuPDF + Groq) para: {pdf_path}")
        
        # 1. Extracción gratuita
        texto_crudo = self._extract_local_text(pdf_path)
        
        if not texto_crudo or len(texto_crudo) < 50:
            print("[!] PDF escaneado detectado. Aquí entraría Gemini 3.6 Flash / LlamaParse.")
            return {"error": "documento_escaneado", "requires_vision": True}
        
        # 2. Estructuración con Groq (Si hay llave configurada)
        if not self.groq_client:
            print("[!] No hay API Key de Groq. Simulando respuesta.")
            return self._mock_response(pdf_path)
            
        prompt = f"""
        Eres un asistente experto en contabilidad. Extrae la siguiente información del texto de este Documento Tributario Electrónico (DTE).
        Debes responder ÚNICAMENTE con un JSON válido. No incluyas explicaciones, ni bloques markdown como ```json.
        
        Estructura requerida:
        {{
            "identificacion": {{
                "codigoGeneracion": "UUID de 36 caracteres",
                "tipoDte": "03, 05, 06 o 14",
                "numeroControl": "DTE-...",
                "fecEmi": "YYYY-MM-DD"
            }},
            "emisor": {{
                "nombre": "Nombre de la empresa",
                "nit": "NIT de la empresa",
                "nrc": "NRC"
            }},
            "resumen": {{
                "totalPagar": 0.00,
                "totalCompra": 0.00,
                "iva": 0.00,
                "ivaPerci1": 0.00,
                "ivaRete1": 0.00
            }},
            "selloRecibido": "Cadena alfanumérica del sello"
        }}
        
        Texto DTE:
        {texto_crudo}
        """
        
        try:
            response = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=1024,
            )
            content = response.choices[0].message.content.strip()
            
            # Limpiar posible markdown residual
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
                
            json_data = json.loads(content)
            return json_data
            
        except Exception as e:
            print(f"[!] Error procesando con Groq: {e}")
            return {"error": "fallo_ia", "mensaje": str(e)}

    def parse_raw_to_standard(self, raw_json: dict) -> dict:
        """Transforma el JSON crudo en el formato estándar del sistema"""
        estandar_json = raw_json.copy()
        estandar_json["_metadata"] = {"fuente": "GROQ_LLAMA3.1", "estandarizado": True}
        return estandar_json
        
    def _mock_response(self, pdf_path: str) -> dict:
        return {
            "identificacion": {
                "tipoDte": "03", 
                "codigoGeneracion": f"GEN-FROM-OCR-{Path(pdf_path).stem}"
            },
            "emisor": {"nombre": "Emisor Detectado IA", "nit": "0000-000000-000-0"},
            "receptor": {"nombre": "Cliente Empresa SA", "nit": "1111-111111-111-1"},
            "resumen": {"totalPagar": 150.00}
        }
