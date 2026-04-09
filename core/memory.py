import uuid
from enum import Enum
from typing import Dict, List, Optional, Any
from utils.logger import logger

class MemoryProtection(Enum):
    READ_ONLY = 1
    WRITE_ONLY = 2
    READ_WRITE = 3
    EXECUTE_ONLY = 4

class MemoryBlock:
    def __init__(self, block_id: str, start_address: int, size: int, pid: int, protection: MemoryProtection):
        self.block_id = block_id
        self.start_address = start_address
        self.size = size
        self.pid = pid
        self.protection = protection
        self.data = bytearray(size)
        self.is_free = False

class VirtualMemoryManager:
    def __init__(self, total_memory_mb: int = 64, block_size: int = 4096):
        self.total_memory = total_memory_mb * 1024 * 1024
        self.block_size = block_size
        self.num_blocks = self.total_memory // self.block_size
        self.blocks: Dict[str, MemoryBlock] = {}
        self.free_list: List[int] = list(range(self.num_blocks))
        self.pid_to_block: Dict[int, str] = {}
        
        logger.debug(f"Memory initialized with {self.num_blocks} blocks of {self.block_size}B", component="MEMORY")
        logger.info(f"VirtualMemoryManager initialized with {total_memory_mb}MB", component="MEMORY")

    def allocate(self, pid: int, size: int, protection: MemoryProtection = MemoryProtection.READ_WRITE) -> Optional[int]:
        if size <= 0:
            logger.error(f"Allocation failed for PID {pid}: Invalid size", component="MEMORY")
            return None

        blocks_needed = (size + self.block_size - 1) // self.block_size
        
        if len(self.free_list) < blocks_needed:
            logger.warning(f"Allocation failed for PID {pid}: Not enough memory", component="MEMORY")
            return None

        allocated_addresses = []
        allocated_block_ids = []
        
        for _ in range(blocks_needed):
            block_index = self.free_list.pop(0)
            address = block_index * self.block_size
            block_id = f"blk_{block_index:08d}"
            
            block = MemoryBlock(
                block_id=block_id,
                start_address=address,
                size=self.block_size,
                pid=pid,
                protection=protection
            )
            
            self.blocks[block_id] = block
            allocated_addresses.append(address)
            allocated_block_ids.append(block_id)

        # Mapeia o PID ao primeiro bloco (simplificação para este teste)
        # Em um sistema real, um processo teria uma lista de blocos
        self.pid_to_block[pid] = allocated_block_ids[0]
        
        first_address = allocated_addresses[0]
        logger.debug(f"Allocated {blocks_needed * self.block_size}B at 0x{first_address:X} for PID {pid} (Block ID: {allocated_block_ids[0]})", component="MEMORY")
        return first_address

    def _get_block_by_pid(self, pid: int) -> Optional[MemoryBlock]:
        block_id = self.pid_to_block.get(pid)
        if not block_id:
            return None
        return self.blocks.get(block_id)

    def write(self, pid: int, offset: int, data: bytes) -> bool:
        block = self._get_block_by_pid(pid)
        if not block:
            logger.error(f"Write failed: Block for PID {pid} not found", component="MEMORY")
            return False

        if block.protection not in [MemoryProtection.WRITE_ONLY, MemoryProtection.READ_WRITE]:
            logger.error(f"Write failed: Protection violation for PID {pid}", component="MEMORY")
            return False

        if offset < 0 or offset + len(data) > block.size:
            logger.error(f"Write failed: Out of bounds for PID {pid}", component="MEMORY")
            return False

        try:
            block.data[offset:offset+len(data)] = data
            return True
        except Exception as e:
            logger.error(f"Write failed for PID {pid}: {str(e)}", component="MEMORY")
            return False

    def read(self, pid: int, offset: int, size: int) -> Optional[bytes]:
        block = self._get_block_by_pid(pid)
        if not block:
            logger.error(f"Read failed: Block for PID {pid} not found", component="MEMORY")
            return None

        if block.protection not in [MemoryProtection.READ_ONLY, MemoryProtection.READ_WRITE]:
            logger.error(f"Read failed: Protection violation for PID {pid}", component="MEMORY")
            return None

        if offset < 0 or offset + size > block.size:
            logger.error(f"Read failed: Out of bounds for PID {pid}", component="MEMORY")
            return None

        try:
            return bytes(block.data[offset:offset+size])
        except Exception as e:
            logger.error(f"Read failed for PID {pid}: {str(e)}", component="MEMORY")
            return None

    def free(self, pid: int) -> bool:
        block_id = self.pid_to_block.pop(pid, None)
        if not block_id:
            logger.warning(f"Free failed: No block found for PID {pid}", component="MEMORY")
            return False

        block = self.blocks.pop(block_id, None)
        if not block:
            return False

        block_index = block.start_address // self.block_size
        self.free_list.append(block_index)
        block.is_free = True
        
        logger.debug(f"Memory freed for PID {pid} (Block ID: {block_id})", component="MEMORY")
        return True

    def get_usage_stats(self) -> Dict[str, Any]:
        total_blocks = self.num_blocks
        used_blocks = total_blocks - len(self.free_list)
        usage_percent = (used_blocks / total_blocks) * 100 if total_blocks > 0 else 0
        
        return {
            "total_memory": self.total_memory,
            "used_memory": used_blocks * self.block_size,
            "free_memory": len(self.free_list) * self.block_size,
            "usage_percent": usage_percent,
            "blocks": used_blocks,
            "total_blocks": total_blocks
        }

# Instância global (opcional, se necessário)
memory_manager = VirtualMemoryManager()