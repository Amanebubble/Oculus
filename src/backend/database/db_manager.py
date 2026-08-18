import sqlite3
from pathlib import Path
from src.backend.utils.config import DB_PATH

class DBManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()
        
    def _get_connection(self):
        # Usar check_same_thread=False si se usa desde múltiples hilos en Pywebview
        return sqlite3.connect(self.db_path, check_same_thread=False)
        
    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla de cuentas de correo para gestión desde la interfaz
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_encrypted TEXT NOT NULL,
                    server TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    active BOOLEAN DEFAULT 1,
                    last_sync DATETIME
                )
            ''')
            
            # Tabla de auditoría e historial de DTEs procesados
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS extraction_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    status TEXT NOT NULL,
                    dte_code TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    error_msg TEXT
                )
            ''')
            conn.commit()

    def get_all_emails(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, server, port, active, last_sync FROM email_accounts")
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def add_email(self, email, password_enc, server, port):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO email_accounts (email, password_encrypted, server, port) VALUES (?, ?, ?, ?)",
                    (email, password_enc, server, port)
                )
                conn.commit()
                return True, "Cuenta añadida correctamente"
            except sqlite3.IntegrityError:
                return False, "La cuenta ya existe"
            except Exception as e:
                return False, str(e)
                
    def log_extraction(self, filename, status, dte_code=None, error_msg=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO extraction_logs (filename, status, dte_code, error_msg) VALUES (?, ?, ?, ?)",
                (filename, status, dte_code, error_msg)
            )
            conn.commit()

    def get_stats(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM extraction_logs WHERE status='VALID_DTE'")
            processed = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM extraction_logs WHERE status='ERROR' OR status='NEEDS_REVIEW'")
            errors = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM extraction_logs WHERE status='OTHER_DTE'")
            others = cursor.fetchone()[0]
            
            return {
                "processed": processed,
                "errors": errors,
                "others": others,
                "pending": 0 # This would be calculated from the physical download folder
            }

# Instancia global
db = DBManager()
