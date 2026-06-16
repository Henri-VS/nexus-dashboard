import psutil
from fastapi import APIRouter

router = APIRouter()


def _r1(v: float) -> float:
    """Round to 1 decimal place."""
    return round(v, 1)


def _gb(bytes_: int) -> float:
    return _r1(bytes_ / 1_073_741_824)  # 1024 ** 3


def _cpu_temp() -> float | None:
    """Best-effort CPU temp from psutil.sensors_temperatures().
    Returns None when not supported (Windows, some Linux configs).
    Checks common sensor key names in priority order.
    """
    try:
        sensors = psutil.sensors_temperatures()
    except AttributeError:
        return None  # not available on this platform (e.g. Windows)

    if not sensors:
        return None

    # Priority order for sensor key names
    for key in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
        if key in sensors and sensors[key]:
            return _r1(sensors[key][0].current)

    # Fallback: first available sensor, first reading
    first_key = next(iter(sensors))
    if sensors[first_key]:
        return _r1(sensors[first_key][0].current)

    return None


@router.get("")
@router.get("/stats")
async def get_system_stats():
    """Return CPU, RAM, disk, temps and battery — always fresh, no cache."""
    cpu   = psutil.cpu_percent(interval=0.5)
    ram   = psutil.virtual_memory()
    disk  = psutil.disk_usage("/")

    # All named sensor readings (for GPU temp keys like 'nvidia_smi' if present)
    raw_temps: dict[str, float] = {}
    try:
        for sensor_name, entries in psutil.sensors_temperatures().items():
            for entry in entries:
                label = entry.label or sensor_name
                key   = f"{sensor_name}:{label}" if entry.label else sensor_name
                raw_temps[key] = _r1(entry.current)
    except AttributeError:
        pass  # Windows / platform without sensor support

    battery      = psutil.sensors_battery()
    cpu_temp_val = _cpu_temp()

    return {
        "cpu_percent":  _r1(cpu),
        "ram_used_gb":  _gb(ram.used),
        "ram_total_gb": _gb(ram.total),
        "ram_percent":  _r1(ram.percent),
        "disk_used_gb":  _gb(disk.used),
        "disk_total_gb": _gb(disk.total),
        "disk_percent":  _r1(disk.percent),
        "cpu_temp":      cpu_temp_val,
        "gpu_temp":      None,
        "temps":         raw_temps,
        "battery_percent": _r1(battery.percent) if battery else None,
        "battery_plugged": battery.power_plugged if battery else None,
    }
