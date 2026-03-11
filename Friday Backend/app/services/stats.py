from typing import Dict, Any
from datetime import datetime
import logging
import psutil

from app.models.state import state

logger = logging.getLogger(__name__)


def get_system_stats() -> Dict[str, Any]:
    try:
        uptime = datetime.now() - state.start_time
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        battery_info = psutil.sensors_battery()
        battery = battery_info.percent if battery_info else 100
        cpu = psutil.cpu_percent(interval=0.1)
        return {
            "battery": round(battery, 1),
            "temperature": round(cpu, 1),
            "cpu": round(cpu, 1),
            "connectivity": "Strong",
            "uptime": f"{hours}h {minutes}m",
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return {
            "battery": 0,
            "temperature": 0,
            "cpu": 0,
            "connectivity": "Unknown",
            "uptime": "0h 0m",
        }
