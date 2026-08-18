import os
import json
import google.generativeai as genai
from pathlib import Path

class OCRService:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.llamaparse_api_key = os.getenv("LLAMA_CLOUD_API_KEY", "")
        
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-pro')

    def extract_text_llamaparse(self, pdf_path: str) -> str:
        """Usa LlamaParse para obtener texto y tablas del PDF con precisión"""
        # Aquí iría la integración real con llama-parse
        # parser = LlamaParse(api_key=self.llamaparse_api_key, result_type="markdown")
        # return parser.load_data(pdf_path)[0].text
        return f"[Texto extraído simulado de {Path(pdf_path).name}]"

    def process_pdf_to_raw_json(self, pdf_path: str) -> dict:
        """
        Tubería principal: LlamaParse -> Gemini/Groq -> JSON Crudo
        """
        print(f"[*] Iniciando OCR Híbrido para: {pdf_path}")
        
        # 1. Extraer texto base
        texto_crudo = self.extract_text_llamaparse(pdf_path)
        
        # 2. Estructurar con LLM (Gemini o Groq)
        prompt = f"""
        Extrae la información de este DTE y devuélvela estrictamente en formato JSON válido.
        Asegúrate de buscar el código de generación y el tipo de DTE.
        
        Texto DTE:
        {texto_crudo}
        """
        
        # Simulación de respuesta de Gemini 100% precisa
        # En producción: response = self.gemini_model.generate_content(prompt)
        # json_data = json.loads(response.text)
        
        raw_json = {
            "identificacion": {
                "tipoDte": "03", 
                "codigoGeneracion": f"GEN-FROM-OCR-{Path(pdf_path).stem}"
            },
            "emisor": {"nombre": "Emisor Detectado IA", "nit": "0000-000000-000-0"},
            "receptor": {"nombre": "Cliente Empresa SA", "nit": "1111-111111-111-1"},
            "resumen": {"totalPagar": 150.00}
        }
        return raw_json

    def parse_raw_to_standard(self, raw_json: dict) -> dict:
        """Transforma el JSON crudo en el formato estándar del sistema"""
        # Aquí se aplicaría la lógica de mapeo para uniformar llaves
        estandar_json = raw_json.copy()
        estandar_json["_metadata"] = {"fuente": "OCR_GEMINI", "estandarizado": True}
        return estandar_json
