import pandas as pd
from pathlib import Path
import json

class ExcelService:
    def __init__(self):
        pass

    def generar_libro_compras(self, client_path: Path, mes_anio: str, save_path: str):
        """
        Lee todos los JSON del cliente en un mes específico y genera el libro de compras en Excel.
        """
        target_dir = client_path / mes_anio
        if not target_dir.exists():
            return False, "No existen datos para ese período."

        jsons = [f for f in target_dir.glob("*.json")]
        if not jsons:
            return False, "No se encontraron documentos en este período."

        filas = []
        for j in jsons:
            with open(j, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
            ident = data.get("identificacion", {})
            emisor = data.get("emisor", {})
            resumen = data.get("resumen", {})
            
            fila = {
                "Fecha Emisión": ident.get("fecEmi"),
                "Tipo DTE": ident.get("tipoDte"),
                "Número Control": ident.get("numeroControl"),
                "NIT Emisor": emisor.get("nit"),
                "Nombre Proveedor": emisor.get("nombre"),
                "Compras Exentas": resumen.get("totalExenta", 0.0),
                "Compras Gravadas": resumen.get("totalGravada", 0.0),
                "IVA": sum(t.get("valor", 0.0) for t in resumen.get("tributos", []) if t.get("codigo") == "20"),
                "Total Compra": resumen.get("totalPagar", 0.0)
            }
            filas.append(fila)

        df = pd.DataFrame(filas)
        excel_path = Path(save_path) / f"Libro_Compras_{client_path.name}_{mes_anio}.xlsx"
        
        # Guardar usando openpyxl
        df.to_excel(excel_path, index=False, engine='openpyxl')
        return True, f"Libro guardado en: {excel_path}"
