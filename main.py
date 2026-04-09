import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import logger
from core.kernel import Kernel
from shell.cli import NexusShell

def print_banner():
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║           N E X U S   C O R E   v0.6-SHELL                ║
    ║      Interactive Command Line Interface Enabled           ║
    ║                                                           ║
    ║   [OK] OMNI Architecture                                  ║
    ║   [OK] Dynamic Modules                                    ║
    ║   [OK] Interactive Shell                                  ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)

async def main_async():
    print_banner()
    logger.info("NEXUS CORE Boot sequence initiated", component="KERNEL")
    
    # Instância Singleton do Kernel
    kernel = Kernel.get_instance()
    
    # Inicializa Módulos Padrão (conforme seu kernel já faz)
    # Nota: Ajuste conforme a inicialização real do seu kernel
    kernel.load_standard_modules() 
    
    # Inicia o Kernel (Loop de Heartbeat) e o Shell simultaneamente
    # O Shell roda como uma tarefa assíncrona dentro do mesmo loop
    shell = NexusShell(kernel)
    
    # Cria tarefas concorrentes
    kernel_task = asyncio.create_task(kernel.run()) # Supondo que kernel.run() seja um loop infinito ou longo
    shell_task = asyncio.create_task(shell.start())
    
    # Aguarda que uma das tarefas termine (geralmente o shell ao digitar 'exit')
    done, pending = await asyncio.wait(
        [kernel_task, shell_task], 
        return_when=asyncio.FIRST_COMPLETED
    )
    
    # Cancela as tarefas pendentes se uma terminar
    for p in pending:
        p.cancel()
        try:
            await p
        except asyncio.CancelledError:
            pass

    logger.info("System shutdown complete.", component="KERNEL")
    print("\n[SYSTEM HALTED] NEXUS CORE session ended successfully.")

def main():
    try:
        asyncio.run(main_async())
    except Exception as e:
        logger.critical(f"System crash: {str(e)}", component="KERNEL")
        print(f"\n[CRITICAL ERROR] {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()