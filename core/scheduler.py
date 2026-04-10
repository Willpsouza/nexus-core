import asyncio
from enum import Enum
from typing import Callable, Any, Dict, List, Optional, Tuple
from utils.logger import logger

class ProcessState(Enum):
    READY = "READY"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    TERMINATED = "TERMINATED"

class Process:
    def __init__(self, pid: int, name: str, task_func: Callable, task_args: tuple, priority: int = 5):
        self.pid = pid
        self.name = name
        self.task_func = task_func  # Armazena a função, não a coroutine
        self.task_args = task_args  # Argumentos originais (sem o pid)
        self.priority = priority
        self.state = ProcessState.READY
        self.memory_blocks: List[int] = []
        self._task_instance: Optional[asyncio.Task] = None

    def create_coroutine(self):
        """Cria a coroutine injetando o PID como primeiro argumento"""
        # Injeta o pid no início dos argumentos
        full_args = (self.pid,) + self.task_args
        return self.task_func(*full_args)

    def __repr__(self):
        return f"Process({self.name}, PID={self.pid}, State={self.state.value})"

class AsyncScheduler:
    def __init__(self):
        self.processes: Dict[int, Process] = {}
        self._next_pid = 1
        self._lock = asyncio.Lock()
        self._running = False
        logger.info("AsyncScheduler initialized", component="SCHEDULER")

    def create_process(self, task_func: Callable, *args, priority: int = 5, name: Optional[str] = None) -> Process:
        """
        Cria um processo registrando a função e argumentos.
        O PID será injetado automaticamente na execução.
        Ex: create_process(minha_funcao, arg1, arg2, priority=5)
        """
        pid = self._next_pid
        self._next_pid += 1
        
        proc_name = name or f"Process-{pid}"
        
        process = Process(pid=pid, name=proc_name, task_func=task_func, task_args=args, priority=priority)
        self.processes[pid] = process
        
        logger.debug(f"Process registered: {process.name} (PID: {pid})", component="SCHEDULER")
        return process

    async def _run_process_logic(self, process: Process):
        """Lógica interna para executar um único processo"""
        try:
            coro = process.create_coroutine()
            process._task_instance = asyncio.create_task(coro)
            await process._task_instance
        except Exception as e:
            logger.error(f"Process {process.name} crashed: {e}", component="SCHEDULER")
        finally:
            process.state = ProcessState.TERMINATED
            logger.info(f"Process terminated: {process.name}", component="SCHEDULER")

    async def run(self):
        """Executa o escalonador Round-Robin simulado"""
        self._running = True
        logger.info("Scheduler started", component="SCHEDULER")

        active_tasks: Dict[int, asyncio.Task] = {}

        while self._running:
            ready_processes = [
                p for p in self.processes.values()
                if p.state != ProcessState.TERMINATED and p.pid not in active_tasks
            ]

            if not ready_processes and not active_tasks:
                logger.info("No active processes. Scheduler idle.", component="SCHEDULER")
                await asyncio.sleep(0.5)
                continue

            ready_processes.sort(key=lambda p: p.priority, reverse=True)

            for proc in ready_processes:
                proc.state = ProcessState.RUNNING
                logger.debug(f"Context switch to: {proc.name} (Priority: {proc.priority})", component="SCHEDULER")
                task = asyncio.create_task(self._run_process_logic(proc))
                active_tasks[proc.pid] = task

            # Poll for completion so we can check _running flag
            while active_tasks:
                if not self._running:
                    for pid, task in active_tasks.items():
                        task.cancel()
                    active_tasks.clear()
                    break

                await asyncio.sleep(0.1)
                finished_pids = [pid for pid, task in active_tasks.items() if task.done()]
                for pid in finished_pids:
                    del active_tasks[pid]

    def stop(self):
        self._running = False
        logger.info("Scheduler stopped", component="SCHEDULER")