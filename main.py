import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import logger
from core.kernel import Kernel
from core.scheduler import AsyncScheduler
from core.memory import VirtualMemoryManager
from modules.base_module import BaseModule, ModuleState

# --- MÓDULO DE EXEMPLO: SystemMonitor ---
class SystemMonitorModule(BaseModule):
    def __init__(self):
        super().__init__("SystemMonitor", "1.0.0")
        self.scheduler = None
        self.memory = None

    async def init(self, kernel: Kernel):
        # Simula obtenção de referências de outros serviços
        # Em um sistema real, isso viria de um Service Locator
        self.scheduler = AsyncScheduler() 
        self.memory = VirtualMemoryManager(total_memory_mb=16)
        logger.info("SystemMonitor attached to Scheduler and Memory", component="SYSMON")

    async def cleanup(self):
        logger.info("SystemMonitor detaching services", component="SYSMON")

    async def handle_event(self, event_type: str, data: any):
        if event_type == "HEARTBEAT":
            logger.debug(f"Monitor received heartbeat: {data}", component="SYSMON")

# --- MÓDULO DE EXEMPLO: VFSModule ---
class VFSModule(BaseModule):
    def __init__(self):
        super().__init__("VFS", "1.2.0")
        self.dependencies = ["SystemMonitor"] # Depende do Monitor estar ativo

    async def init(self, kernel: Kernel):
        logger.info("VFS Module initializing file structures", component="VFS")
        # Simula criação de root
        await asyncio.sleep(0.1)
        logger.info("VFS Root '/' mounted", component="VFS")

# -----------------------------------------

def print_banner(version: str):
    banner = f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║           N E X U S   C O R E   {version}                 ║
    ║      OMNI-ARCHITECTURE (Dynamic Kernel + Modules)         ║
    ║                                                           ║
    ║   [OK] Logger System                                      ║
    ║   [OK] Micro-Kernel Core                                  ║
    ║   [OK] System Bus (Pub/Sub)                               ║
    ║   [--] Loading Dynamic Modules...                         ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)

async def main_async():
    print_banner("v0.5-OMNI")
    logger.info("NEXUS CORE Boot sequence initiated", component="KERNEL")

    # 1. Inicializa o Kernel Singleton
    kernel = Kernel()

    # 2. Cria e Carrega Módulos Dinamicamente
    # Note como é fácil adicionar/remover funcionalidades agora
    monitor = SystemMonitorModule()
    vfs = VFSModule()

    logger.info("Loading dynamic modules...", component="KERNEL")
    
    # Carrega Monitor primeiro
    if not await kernel.register_module(monitor):
        logger.critical("Failed to load critical module: SystemMonitor", component="KERNEL")
        return

    # Carrega VFS (que depende do Monitor)
    if not await kernel.register_module(vfs):
        logger.error("Failed to load module: VFS", component="KERNEL")
        # Continua mesmo assim para demonstrar resiliência, ou poderia abortar

    # 3. Teste do System Bus
    logger.info("Testing System Bus communication...", component="KERNEL")
    await kernel.sysbus.publish("HEARTBEAT", {"uptime": 0, "status": "green"})

    # 4. Roda o Loop do Kernel por um tempo determinado
    try:
        # Cria uma tarefa para o kernel rodar
        kernel_task = asyncio.create_task(kernel.run())
        
        # Simula execução do sistema por 3 segundos
        await asyncio.sleep(3)
        
        # Envia sinal de shutdown via Bus
        await kernel.sysbus.publish("SYSTEM_SHUTDOWN")
        
        # Aguarda o kernel terminar gracefully
        await kernel_task
        
    except Exception as e:
        logger.critical(f"Kernel Panic: {e}", component="KERNEL")
        raise

    logger.info("System shutdown complete.", component="KERNEL")
    print("\n[SYSTEM HALTED] NEXUS CORE session ended successfully.")

def main():
    try:
        asyncio.run(main_async())
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()