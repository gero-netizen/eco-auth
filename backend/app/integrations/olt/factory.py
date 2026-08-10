from app.core.config import Settings

from .base import OltGateway
from .simulator import SimulatedOltGateway


def build_olt_gateway(settings: Settings) -> OltGateway:
    if settings.olt_mode == "simulated":
        return SimulatedOltGateway()
    raise RuntimeError(f"OLT mode '{settings.olt_mode}' has no installed adapter")

