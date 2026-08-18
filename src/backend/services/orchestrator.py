import time
import threading
from src.backend.database.db_manager import db
from src.backend.services.email_service import EmailService
from src.backend.services.dte_service import DTEService
from src.backend.utils.config import CARPETA_DESCARGAS

class Orchestrator:
    def __init__(self):
        self.running = False
        self.thread = None
        self.email_service = EmailService(str(CARPETA_DESCARGAS))
        self.dte_service = DTEService()
        
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
            print("[Orquestador] Motor iniciado en segundo plano.")
            
    def stop(self):
        if self.running:
            print("[Orquestador] Apagando el motor. Esperando al final del ciclo actual...")
            self.running = False
            
    def _loop(self):
        while self.running:
            try:
                print("\n=== [Orquestador] Iniciando Ciclo ===")
                
                # FASE 1: Descarga de Correos
                cuentas = db.get_all_emails()
                cuentas_activas = [c for c in cuentas if c.get('active')]
                
                for cuenta in cuentas_activas:
                    if not self.running: break
                    
                    email = cuenta['email']
                    password = cuenta['password_encrypted']
                    servidor = cuenta['server']
                    puerto = cuenta['port']
                    
                    # Detección Automática de Protocolo
                    protocolo = "POP3" if puerto == 995 else "IMAP"
                    
                    try:
                        resultados = self.email_service.descargar_correos(
                            cuenta=email,
                            servidor=servidor,
                            puerto=puerto,
                            usuario=email,
                            password=password,
                            protocolo=protocolo
                        )
                        print(f"[Orquestador] Cuenta {email}: {resultados}")
                        db.update_email_status(email, 1) # Marcar como activa/ok
                    except Exception as e:
                        print(f"[Orquestador] Error de autenticación o conexión descargando {email}: {e}")
                        db.update_email_status(email, 0) # Desactivar cuenta por error
                        # Continuar con la siguiente cuenta sin detener el ciclo principal
                        
                    # Pausa Táctica para evitar saturación de red o del servidor IMAP/POP3
                    if self.running:
                        print("  [Pausing 10s...]")
                        time.sleep(10)
                        
                # FASE 2 y 3: Procesamiento y Archivado
                if self.running:
                    print("\n[Orquestador] Procesando descargas acumuladas...")
                    res = self.dte_service.process_downloads()
                    print(f"[Orquestador] Resultados del procesamiento: {res}")
                
            except Exception as e:
                print(f"[Orquestador] Error crítico en el ciclo: {e}")
                
            # FASE 4: Pausa profunda antes de reiniciar el ciclo (10 minutos)
            if self.running:
                espera_segundos = 600
                print(f"\n=== [Orquestador] Ciclo Finalizado. Durmiendo {espera_segundos}s ===")
                # Sleep en pequeños bloques para responder rápido al comando de Stop
                for _ in range(espera_segundos):
                    if not self.running: break
                    time.sleep(1)
                    
        print("[Orquestador] Motor detenido exitosamente.")
