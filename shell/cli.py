import asyncio
import sys
from typing import Optional, List
from utils.logger import logger

class NexusShell:
    def __init__(self, kernel):
        self.kernel = kernel
        self.running = False
        self.prompt = "nexus> "
        self.commands = {
            'help': self.cmd_help,
            'clear': self.cmd_clear,
            'exit': self.cmd_exit,
            'ls': self.cmd_ls,
            'cd': self.cmd_cd,
            'pwd': self.cmd_pwd,
            'mkdir': self.cmd_mkdir,
            'touch': self.cmd_touch,
            'cat': self.cmd_cat,
            'rm': self.cmd_rm,
            'ps': self.cmd_ps,
            'mem': self.cmd_mem,
        }
        logger.info("NEXUS CLI initialized", component="SHELL")

    async def start(self):
        self.running = True
        print("\n╭────────────────────────────────────────────────────────────╮")
        print("│  N E X U S   C L I   v1.0  -  Type 'help' for commands   │")
        print("╰────────────────────────────────────────────────────────────╯\n")
        
        loop = asyncio.get_event_loop()
        
        while self.running:
            try:
                # Leitura assíncrona de input (não bloqueia o kernel)
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                cmd = parts[0].lower()
                args = parts[1:]

                if cmd in self.commands:
                    try:
                        await self.commands[cmd](args)
                    except Exception as e:
                        print(f"[ERROR] Command '{cmd}' failed: {str(e)}")
                        logger.error(f"CLI Command error: {cmd} - {e}", component="SHELL")
                else:
                    print(f"[UNKNOWN] Command '{cmd}' not found. Type 'help'.")
                    
            except KeyboardInterrupt:
                print("\nUse 'exit' to shut down the system gracefully.")
            except EOFError:
                self.running = False

    async def cmd_help(self, args: List[str]):
        print("Available Commands:")
        print("  System:  help, clear, exit")
        print("  Files:   ls, cd, pwd, mkdir, touch, cat, rm")
        print("  Process: ps, kill <pid>")
        print("  Memory:  mem")

    async def cmd_clear(self, args: List[str]):
        print("\n" * 50)

    async def cmd_exit(self, args: List[str]):
        print("Shutting down NEXUS CORE...")
        self.running = False
        # Aciona o shutdown do kernel
        asyncio.create_task(self.kernel.shutdown())

    async def cmd_ls(self, args: List[str]):
        path = args[0] if args else "."
        fs = self.kernel.get_module('VFS')
        if fs:
            content = fs.list_directory(path)
            if content:
                print("  " + "\n  ".join(content))
            else:
                print("[EMPTY] Directory is empty or path invalid.")
        else:
            print("[ERROR] VFS module not available.")

    async def cmd_cd(self, args: List[str]):
        if not args:
            print("[ERROR] Usage: cd <path>")
            return
        path = args[0]
        fs = self.kernel.get_module('VFS')
        if fs and fs.cd(path):
            pass  # Success — silently change directory
        else:
            print(f"[ERROR] Failed to change directory to '{path}'")

    async def cmd_pwd(self, args: List[str]):
        fs = self.kernel.get_module('VFS')
        if fs:
            print(fs.get_current_path())

    async def cmd_mkdir(self, args: List[str]):
        if not args:
            print("[ERROR] Usage: mkdir <name>")
            return
        fs = self.kernel.get_module('VFS')
        if fs and fs.create_directory(args[0]):
            print(f"[OK] Directory '{args[0]}' created.")
        else:
            print(f"[ERROR] Failed to create directory '{args[0]}'.")

    async def cmd_touch(self, args: List[str]):
        if not args:
            print("[ERROR] Usage: touch <filename>")
            return
        fs = self.kernel.get_module('VFS')
        if fs and fs.create_file(args[0]):
            print(f"[OK] File '{args[0]}' created.")
        else:
            print(f"[ERROR] Failed to create file '{args[0]}'.")

    async def cmd_cat(self, args: List[str]):
        if not args:
            print("[ERROR] Usage: cat <filename>")
            return
        fs = self.kernel.get_module('VFS')
        if fs:
            content = fs.read_file(args[0])
            if content is not None:
                print(content)
            else:
                print(f"[ERROR] Could not read file '{args[0]}'.")

    async def cmd_rm(self, args: List[str]):
        if not args:
            print("[ERROR] Usage: rm <name>")
            return
        fs = self.kernel.get_module('VFS')
        if fs and fs.remove(args[0]):
            print(f"[OK] '{args[0]}' removed.")
        else:
            print(f"[ERROR] Failed to remove '{args[0]}'.")

    async def cmd_ps(self, args: List[str]):
        sched = self.kernel.get_module('AsyncScheduler')
        if sched:
            print("PID\tNAME\t\tSTATE\tPRIORITY")
            print("-" * 40)
            for pid, proc in sched.processes.items():
                print(f"{pid}\t{proc.name}\t\t{proc.state.value}\t{proc.priority}")
        else:
            print("[ERROR] Scheduler module not available.")

    async def cmd_mem(self, args: List[str]):
        mem = self.kernel.get_module('VirtualMemoryManager')
        if mem:
            stats = mem.get_usage_stats()
            total_mb = stats['total_memory'] / (1024 * 1024)
            used_mb = stats['used_memory'] / (1024 * 1024)
            print(f"Total Memory: {total_mb:.0f} MB")
            print(f"Used: {used_mb:.2f} MB ({stats['usage_percent']:.2f}%)")
            print(f"Active Blocks: {stats['blocks']}")
        else:
            print("[ERROR] Memory module not available.")