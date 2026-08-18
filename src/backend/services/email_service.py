import os
import re
import datetime
import json
from pathlib import Path
from imap_tools import MailBox, AND

class EmailService:
    def __init__(self, download_dir: str):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Palabras maestras para detectar DTEs con asuntos raros
        self.palabras_clave_asunto = [
            "dte", "documento", "facturacion", "facturación", 
            "credito fiscal", "crédito fiscal", "ccf",
            "factura", "comprobante", "emisión", "emision", "adjunto", "envio",
            "autofacil", "recibo", "nota"
        ]
        
    def _asunto_coincide(self, asunto: str) -> bool:
        """Filtro de seguridad para el asunto del correo."""
        asunto_lower = (asunto or "").lower().strip()
        # Correos sin asunto pasan por si acaso
        if not asunto_lower:
            return True
        return any(p.lower() in asunto_lower for p in self.palabras_clave_asunto)

    def _nombre_seguro(self, nombre: str) -> str:
        # Extraer el nombre base y la extensión
        partes = nombre.rsplit('.', 1)
        if len(partes) == 2:
            base, ext = partes
            base_limpia = re.sub(r"[^A-Za-z0-9_.-]", "_", base)
            return f"{base_limpia}.{ext}"
        else:
            return re.sub(r"[^A-Za-z0-9_.-]", "_", nombre)

    def _procesar_mensaje_generico(self, cuenta: str, uid: str, subject: str, msg_date: datetime.datetime, adjuntos_raw: list, resultados: dict):
        """Descarga cruda y segura usando el UID del correo y nombre original."""
        if not self._asunto_coincide(subject):
            return
            
        # Filtrar extensiones válidas
        adjuntos = [att for att in adjuntos_raw if att['filename'].lower().endswith(('.pdf', '.json'))]
        if not adjuntos:
            return
            
        fecha_str = msg_date.strftime("%d%m%Y")
        cuenta_upper = cuenta.upper()
        
        for att in adjuntos:
            nombre_original_limpio = self._nombre_seguro(att['filename'])
            # Estructura: ALIAS_UID_FECHA_nombreoriginal.ext
            nombre_final = f"{cuenta_upper}_{uid}_{fecha_str}_{nombre_original_limpio}"
            ruta_destino = self.download_dir / nombre_final
            
            # Anti-colisión por si por alguna locura el mismo correo trae dos archivos llamados igual
            contador = 1
            while ruta_destino.exists():
                partes = nombre_final.rsplit('.', 1)
                if len(partes) == 2:
                    nombre_final = f"{partes[0]}_{contador}.{partes[1]}"
                else:
                    nombre_final = f"{nombre_final}_{contador}"
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
                
                dt = msg.date if msg.date else datetime.datetime.now()
                self._procesar_mensaje_generico(cuenta, msg.uid, msg.subject, dt, adjuntos_raw, resultados)
                    
            mailbox.logout()
        except Exception as e:
            print(f"[!] Error IMAP en {cuenta}: {e}")
            raise e
            
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
                
                if uid in estado_descargas[cuenta]:
                    continue
                    
                resultados["revisados"] += 1
                
                # Descargar mensaje
                _, lineas, _ = conn.retr(i)
                raw_email = b'\r\n'.join(lineas)
                msg = email.message_from_bytes(raw_email)
                
                date_tuple = email.utils.parsedate_tz(msg.get("Date"))
                if date_tuple:
                    dt = email.utils.to_datetime(date_tuple)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=datetime.timezone.utc)
                    if dt < fecha_corte:
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
                
                estado_descargas[cuenta].append(uid)
                
            conn.quit()
            
            with open(estado_file, "w") as f:
                json.dump(estado_descargas, f)
                
        except Exception as e:
            print(f"[!] Error POP3 en {cuenta}: {e}")
            raise e
            
        return resultados
