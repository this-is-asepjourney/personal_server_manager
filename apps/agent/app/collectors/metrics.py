import platform
import time
import psutil
from typing import Dict, Any

_last_net_io = None
_last_net_time = None

def get_system_info() -> Dict[str, Any]:
    uname = platform.uname()
    return {
        "hostname": uname.node,
        "os_name": uname.system,
        "os_version": uname.release,
        "architecture": uname.machine,
        "processor": uname.processor,
        "python_version": platform.python_version()
    }

def get_metrics_snapshot() -> Dict[str, Any]:
    global _last_net_io, _last_net_time
    
    # CPU
    cpu_percent = psutil.cpu_percent(interval=None)
    
    # Memory
    mem = psutil.virtual_memory()
    
    # Disk
    disk = psutil.disk_usage('/') if platform.system() != 'Windows' else psutil.disk_usage('C:\\')
    
    # Network delta
    net_io = psutil.net_io_counters()
    now = time.time()
    
    rx_rate = 0.0
    tx_rate = 0.0
    if _last_net_io and _last_net_time:
        elapsed = max(now - _last_net_time, 0.001)
        rx_rate = (net_io.bytes_recv - _last_net_io.bytes_recv) / elapsed
        tx_rate = (net_io.bytes_sent - _last_net_io.bytes_sent) / elapsed
        
    _last_net_io = net_io
    _last_net_time = now
    
    # Uptime
    boot_time = psutil.boot_time()
    uptime_seconds = int(now - boot_time)

    return {
        "cpu_usage": round(cpu_percent, 1),
        "memory_usage": round(mem.percent, 1),
        "memory_used_bytes": mem.used,
        "memory_total_bytes": mem.total,
        "disk_usage": round(disk.percent, 1),
        "disk_used_bytes": disk.used,
        "disk_total_bytes": disk.total,
        "network_rx_bytes_per_sec": round(rx_rate, 1),
        "network_tx_bytes_per_sec": round(tx_rate, 1),
        "uptime_seconds": uptime_seconds
    }

