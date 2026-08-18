import os
import json
import re
import datetime
from pathlib import Path
from imap_tools import MailBox, AND
import fitz  # PyMuPDF

class EmailService:
    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Palabras maestras del sistema anterior para detectar DTEs con asuntos raros
        self.palabras_clave_asunto = [
            "dte", "documento", "facturacion", "facturación", 
            "credito fiscal", "crédito fiscal", "ccf",
            "factura", "comprobante", "emisión", "emision", "adjunto", "envio",
            "autofacil", "recibo", "nota"
        ]
        
        # Campos obligatorios en JSON para considerarlo DTE
        self.campos_dte_esperados = ["identificacion", "emisor", "receptor"]
        
    def _asunto_coincide(self, asunto: str) -> bool:
        """Filtro de seguridad para el asunto del correo."""
        asunto_lower = (asunto or "").lower().strip()
        # Correos sin asunto pasan por si acaso
        if not asunto_lower:
            return True
        return any(p.lower() in asunto_lower for p in self.palabras_clave_asunto)

    def _es_json_valido(self, contenido_bytes: bytes) -> tuple:
        """Valida que un JSON sea un DTE estructurado y extrae el UUID."""
        try:
            try:
                texto = contenido_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                texto = contenido_bytes.decode("latin-1")
                
            data = json.loads(texto)
        except Exception:
            return False, None
            
        if all(campo in data for campo in self.campos_dte_esperados):
            return True, data
        return False, None

    def _extraer_uuid_pdf(self, contenido_bytes: bytes) -> str:
        """Lectura ligera con PyMuPDF para extraer el UUID del DTE."""
        try:
            doc = fitz.open(stream=contenido_bytes, filetype="pdf")
            if len(doc) == 0:
                return ""
            
            # Buscar solo en la primera página para mayor velocidad
            texto = doc[0].get_text()
            
            # UUID Regex
            match_uuid = re.search(r'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}', texto)
            if match_uuid:
                return match_uuid.group(0).upper()
                
            # Sello Recepcion Regex
            match_sello = re.search(r'(?:sello\s+recepcion|sello\s+de\s+recepci[\w]*)\s*[:=]?\s*([a-zA-Z0-9]{30,45})', texto, re.IGNORECASE)
            if match_sello:
                return match_sello.group(1).upper()
                
        except Exception as e:
            print(f"[!] Error extrayendo UUID del PDF: {e}")
        return ""

    def _nombre_seguro(self, nombre: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]", "_", nombre)

    def _procesar_mensaje_generico(self, cuenta: str, uid: str, subject: str, msg_date: datetime.datetime, adjuntos_raw: list, resultados: dict):
        """Lógica común para validar y guardar adjuntos (usada por IMAP y POP3)."""
        if not self._asunto_coincide(subject):
            return
            
        # Filtrar extensiones válidas
        adjuntos = [att for att in adjuntos_raw if att['filename'].lower().endswith(('.pdf', '.json'))]
        if not adjuntos:
            return
            
        # Pasada 1: Intentar buscar el UUID en JSON o PDF
        uuid_dte = ""
        for att in adjuntos:
            ext = att['filename'].lower().split('.')[-1]
            if ext == "json":
                valido, data = self._es_json_valido(att['payload'])
                if valido:
                    uuid_dte = data.get("identificacion", {}).get("codigoGeneracion", "")
                    if uuid_dte: break
                    
        if not uuid_dte:
            for att in adjuntos:
                if att['filename'].lower().endswith(".pdf"):
                    uuid_dte = self._extraer_uuid_pdf(att['payload'])
                    if uuid_dte: break
                    
        identificador = uuid_dte or "UNKNOWN"
        fecha_str = msg_date.strftime("%d%m%Y")
        
        # Pasada 2: Guardar archivos
        for att in adjuntos:
            ext = att['filename'].lower().split('.')[-1]
            if ext == "json":
                valido, _ = self._es_json_valido(att['payload'])
                if not valido:
                    continue
                    
            base_nombre = self._nombre_seguro(f"{cuenta}_UID{uid}_{identificador}_{fecha_str}")
            nombre_final = f"{base_nombre}.{ext}"
            ruta_destino = self.download_dir / nombre_final
            
            contador = 1
            while ruta_destino.exists():
                nombre_final = f"{base_nombre}_{contador}.{ext}"
                ruta_destino = self.download_dir / nombre_final
                contador += 1
                
            with open(ruta_destino, "wb") as f:
                f.write(att['payload'])
                
            resultados["descargados"] += 1
            print(f"  [+] Descargado: {nombre_final}")

    def descargar_correos(self, cuenta: str, servidor: str, puerto: int, usuario: str, password: str, carpeta: str = "INBOX", protocolo: str = "IMAP"):
        """Punto de entrada principal para IMAP o POP3."""
        print(f"[*] Iniciando descarga ({protocolo}) para {usuario} en {servidor}")
        if protocolo.upper() == "POP3":
            return self._descargar_pop3(cuenta, servidor, puerto, usuario, password)
        else:
            return self._descargar_imap(cuenta, servidor, puerto, usuario, password, carpeta)

    def _descargar_imap(self, cuenta: str, servidor: str, puerto: int, usuario: str, password: str, carpeta: str):
        resultados = {"revisados": 0, "descargados": 0, "errores": 0}
        fecha_corte = datetime.date(2026, 7, 1)
        
        try:
            mailbox = MailBox(servidor, port=puerto, timeout=60).login(usuario, password, initial_folder=carpeta)
            criterio = AND(date_gte=fecha_corte)
            
            for msg in mailbox.fetch(criterio, mark_seen=False):
                resultados["revisados"] += 1
                adjuntos_raw = [{'filename': att.filename, 'payload': att.payload} for att in msg.attachments]
                
                # Para IMAP, si la fecha es None por algún error, fallback
                dt = msg.date if msg.date else datetime.datetime.now()
                self._procesar_mensaje_generico(cuenta, msg.uid, msg.subject, dt, adjuntos_raw, resultados)
                    
            mailbox.logout()
        except Exception as e:
            print(f"[!] Error IMAP en {cuenta}: {e}")
            resultados["errores"] += 1
            
        return resultados

    def _descargar_pop3(self, cuenta: str, servidor: str, puerto: int, usuario: str, password: str):
        import poplib
        import email
        import email.utils
        
        resultados = {"revisados": 0, "descargados": 0, "errores": 0}
        fecha_corte = datetime.datetime(2026, 7, 1, tzinfo=datetime.timezone.utc)
        
        estado_file = self.download_dir / "pop3_estado.json"
        estado_descargas = {}
        if estado_file.exists():
            try:
                with open(estado_file, "r") as f:
                    estado_descargas = json.load(f)
            except: pass
            
        if cuenta not in estado_descargas:
            estado_descargas[cuenta] = []
            
        try:
            conn = poplib.POP3_SSL(servidor, puerto)
            conn.user(usuario)
            conn.pass_(password)
            
            # Obtener UIDs estables del servidor
            resp, items, octets = conn.uidl()
            uidls = {}
            for item in items:
                idx, uid = item.decode().split(' ')
                uidls[int(idx)] = uid
                
            num_msgs = len(conn.list()[1])
            print(f"  [POP3] {num_msgs} mensajes en el servidor.")
            
            for i in range(1, num_msgs + 1):
                uid = uidls.get(i, str(i))
                
                # Si ya lo procesamos, saltarlo rápido (esto hace POP3 usable)
                if uid in estado_descargas[cuenta]:
                    continue
                    
                resultados["revisados"] += 1
                
                # Descargar mensaje
                _, lineas, _ = conn.retr(i)
                raw_email = b'\r\n'.join(lineas)
                msg = email.message_from_bytes(raw_email)
                
                # Filtrar fecha manualmente
                date_tuple = email.utils.parsedate_tz(msg.get("Date"))
                if date_tuple:
                    dt = email.utils.to_datetime(date_tuple)
                    # Comparar offset-aware
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=datetime.timezone.utc)
                    if dt < fecha_corte:
                        # Guardamos en estado para no volver a descargar un correo viejo
                        estado_descargas[cuenta].append(uid)
                        continue
                else:
                    dt = datetime.datetime.now()
                    
                subject = str(msg.get("Subject", ""))
                
                adjuntos_raw = []
                for part in msg.walk():
                    if part.get_content_maintype() == 'multipart': continue
                    filename = part.get_filename()
                    if not filename: continue
                    payload = part.get_payload(decode=True)
                    if payload:
                        adjuntos_raw.append({'filename': filename, 'payload': payload})
                        
                self._procesar_mensaje_generico(cuenta, uid, subject, dt, adjuntos_raw, resultados)
                
                # Marcar como procesado localmente
                estado_descargas[cuenta].append(uid)
                
            conn.quit()
            
            # Guardar estado
            with open(estado_file, "w") as f:
                json.dump(estado_descargas, f)
                
        except Exception as e:
            print(f"[!] Error POP3 en {cuenta}: {e}")
            resultados["errores"] += 1
            
        return resultados
