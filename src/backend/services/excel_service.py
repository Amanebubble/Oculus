import json
import pandas as pd
from pathlib import Path

class ExcelService:
    def __init__(self):
        self.columns = [
            'No. Correlativo', 'Fecha de Emision', 'CODIGO DE GENERACION', 'N.R.C.', 
            'NIT,CIP,DUI del Sujeto Excluido', 'Nombre del Proveedor', 'Compras a Sujetos Excluidos', 
            'FOVIAL/ COTRANS/ CESC', 'COMPRAS EXENTAS - Internas', 'COMPRAS EXENTAS - Importaciones', 
            'COMPRAS GRAVADAS - Internas', 'COMPRAS GRAVADAS - Importaciones', 'Credito Fiscal', 
            'IVA Percibido', 'TOTAL Compras', 'Impuesto 0.02', 'Impuesto Retenido a Terceros', 
            'COMPRAS NO SUJETAS', 'SERIE / SELLO DE RECEPCION', 'No DE CONTROL /RESOLUCION', 
            'TIPO DE OPERACION', 'CLASIFICACION', 'TIPO DE COSTO /GASTO', 'CONCEPTO IVA'
        ]

    def _get_iva(self, tributos):
        if not tributos: return 0.0
        for t in tributos:
            if str(t.get("codigo", "")) == "20" or "iva" in str(t.get("descripcion", "")).lower():
                return float(t.get("valor", 0.0))
        return 0.0

    def generar_libro_compras(self, carpeta_cliente: Path, mes_anio: str, save_path: str):
        """Lee los JSONs de un mes específico y genera el libro de compras oficial."""
        try:
            target_dir = carpeta_cliente / mes_anio
            if not target_dir.exists():
                return False, f"La carpeta de datos {mes_anio} no existe."
                
            jsons_files = list(target_dir.glob("*.json"))
            if not jsons_files:
                return False, "No hay documentos JSON para generar el reporte."
                
            rows = []
            correlativo = 1
            
            for jf in jsons_files:
                try:
                    with open(jf, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    identificacion = data.get("identificacion", {})
                    emisor = data.get("emisor", {})
                    receptor = data.get("receptor", {})
                    resumen = data.get("resumen", {})
                    sello_dict = data.get("selloRecepcion", {})
                    
                    row = {col: "" for col in self.columns}
                    
                    row['No. Correlativo'] = correlativo
                    row['Fecha de Emision'] = identificacion.get("fecEmi", "")
                    row['CODIGO DE GENERACION'] = identificacion.get("codigoGeneracion", "")
                    
                    # Proveedor (Emisor)
                    row['N.R.C.'] = emisor.get("nrc", "")
                    row['NIT,CIP,DUI del Sujeto Excluido'] = emisor.get("nit", "")
                    row['Nombre del Proveedor'] = emisor.get("nombre", "Desconocido")
                    
                    # Montos
                    row['COMPRAS GRAVADAS - Internas'] = float(resumen.get("totalGravada", 0.0) or resumen.get("subTotal", 0.0))
                    row['Credito Fiscal'] = self._get_iva(resumen.get("tributos", []))
                    
                    # Otros Impuestos (Si es revisión manual o IA lo saca)
                    otros_impuestos = data.get("otros_impuestos_manuales", 0.0)
                    if otros_impuestos > 0:
                        row['FOVIAL/ COTRANS/ CESC'] = otros_impuestos
                        
                    row['TOTAL Compras'] = float(resumen.get("totalPagar", 0.0) or resumen.get("montoTotalOperacion", 0.0))
                    
                    # Controles
                    row['SERIE / SELLO DE RECEPCION'] = sello_dict.get("selloRecepcion", "")
                    row['No DE CONTROL /RESOLUCION'] = identificacion.get("numeroControl", "")
                    
                    rows.append(row)
                    correlativo += 1
                except Exception as e:
                    print(f"Error parseando {jf.name}: {e}")
                    
            df = pd.DataFrame(rows)
            df.to_excel(save_path, index=False)
            
            return True, "Libro de compras generado exitosamente."
            
        except Exception as e:
            return False, f"Error general: {str(e)}"
