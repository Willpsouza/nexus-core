import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import logger
from core.scheduler import AsyncScheduler
from core.memory import VirtualMemoryManager, MemoryProtection
from core.vfs import VirtualFileSystem

def print_banner(version: str):
    banner = f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║           N E X U S   C O R E   {version}                 ║
    ║      Full System Integration (Scheduler+Mem+VFS)          ║
    ║                                                           ║
    ║   [OK] Logger System                                      ║
    ║   [OK] Process Scheduler                                  ║
    ║   [OK] Virtual Memory Manager                             ║
    ║   [OK] Virtual File System                                ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)

async def system_task(pid: int, name: str, scheduler: AsyncScheduler, mem: VirtualMemoryManager, fs: VirtualFileSystem):
    logger.info(f"Process {name} (PID {pid}) starting system operations", component="TASK")
    
    # 1. Operações de Memória
    addr = mem.allocate(pid, 2048, MemoryProtection.READ_WRITE)
    if addr is None:
        logger.error(f"Memory allocation failed for {name}", component="TASK")
        return
    
    data = f"Data from process {name}".encode()
    mem.write(pid, 0, data)
    await asyncio.sleep(0.2)
    read_back = mem.read(pid, 0, len(data))
    
    if read_back == data:
        logger.debug(f"Memory integrity OK for {name}", component="TASK")
    else:
        logger.error(f"Memory corruption in {name}", component="TASK")
    
    # 2. Operações de Arquivo
    file_path = f"/data/{name}_log.txt"
    fs.touch(file_path)
    fs.write_file(file_path, data + b" - persisted to VFS")
    
    content = fs.read_file(file_path)
    if content and b"persisted to VFS" in content:
        logger.debug(f"VFS integrity OK for {name}", component="TASK")
    else:
        logger.error(f"VFS read error for {name}", component="TASK")
    
    # Libera memória
    mem.free(pid)
    logger.info(f"Process {name} completed successfully", component="TASK")

async def run_full_integration_test():
    logger.info("Starting Full System Integration Test...", component="KERNEL")
    
    # Inicializa componentes
    scheduler = AsyncScheduler()
    mem_manager = VirtualMemoryManager(total_memory_mb=8)
    fs_system = VirtualFileSystem()

    # Configura estrutura de diretórios básica
    fs_system.mkdir("/data")
    fs_system.mkdir("/home")
    fs_system.cd("/data")
    logger.info(f"Root contents: {fs_system.ls('/')}", component="VFS")

    # Cria processos SEM passar o pid explicitamente
    # A assinatura da tarefa deve ser: async def task(pid, nome, scheduler, mem, fs)
    p1 = scheduler.create_process(system_task, "SysWorker_A", scheduler, mem_manager, fs_system, priority=5)
    p2 = scheduler.create_process(system_task, "SysWorker_B", scheduler, mem_manager, fs_system, priority=3)
    
    logger.info(f"Created 2 integrated processes.", component="KERNEL")
    
    try:
        # Executa por 5 segundos
        await asyncio.wait_for(scheduler.run(), timeout=5.0)
    except asyncio.TimeoutError:
        logger.info("Integration test duration completed.", component="KERNEL")
    
    scheduler.stop()
    
    final_stats = mem_manager.get_usage_stats()
    logger.info(f"Final Memory Usage: {final_stats['usage_percent']:.2f}%", component="KERNEL")

def main():
    try:
        print_banner("v0.4-ALPHA")
        logger.info("NEXUS CORE Boot sequence initiated", component="KERNEL")
        
        asyncio.run(run_full_integration_test())
        
        logger.info("System shutdown sequence initiated...", component="KERNEL")
        print("\n[SYSTEM HALTED] NEXUS CORE session ended successfully.")
        
    except Exception as e:
        logger.critical(f"System crash: {str(e)}", component="KERNEL")
        print(f"\n[CRITICAL ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()