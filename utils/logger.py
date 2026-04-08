import datetime
import os
from enum import Enum
from typing import Optional

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Logger:
    def __init__(self, log_file: str = "nexus.log", max_size_mb: int = 10):
        self.log_file = log_file
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._ensure_log_directory()
        
    def _ensure_log_directory(self):
        """Garante que o diretório de logs exista"""
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    
    def _rotate_if_needed(self):
        """Realiza rotação de log se exceder o tamanho máximo"""
        if os.path.exists(self.log_file) and os.path.getsize(self.log_file) > self.max_size_bytes:
            backup_name = f"{self.log_file}.old"
            if os.path.exists(backup_name):
                os.remove(backup_name)
            os.rename(self.log_file, backup_name)
    
    def _write_log(self, level: LogLevel, message: str, component: Optional[str] = None):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        component_str = f"[{component}]" if component else "[SYSTEM]"
        log_entry = f"[{timestamp}] {level.value:<8} {component_str} {message}\n"
        
        self._rotate_if_needed()
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        
        print(log_entry.strip())
    
    def debug(self, message: str, component: Optional[str] = None):
        self._write_log(LogLevel.DEBUG, message, component)
    
    def info(self, message: str, component: Optional[str] = None):
        self._write_log(LogLevel.INFO, message, component)
    
    def warning(self, message: str, component: Optional[str] = None):
        self._write_log(LogLevel.WARNING, message, component)
    
    def error(self, message: str, component: Optional[str] = None):
        self._write_log(LogLevel.ERROR, message, component)
    
    def critical(self, message: str, component: Optional[str] = None):
        self._write_log(LogLevel.CRITICAL, message, component)

# Instância global do logger
logger = Logger()
