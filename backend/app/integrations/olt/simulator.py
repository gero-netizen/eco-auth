from .base import OltGateway, OnuState


class SimulatedOltGateway(OltGateway):
    """Deterministic bench substitute; never opens a network connection."""

    def __init__(self) -> None:
        self._onus: dict[str, OnuState] = {
            "SIMONU0001": OnuState("SIMONU0001", "unconfigured", -19.2),
        }

    async def discover(self) -> list[OnuState]:
        return list(self._onus.values())

    async def provision(self, serial: str, profile: str) -> OnuState:
        state = OnuState(serial.upper(), "online", -19.2, profile)
        self._onus[state.serial] = state
        return state

    async def get_state(self, serial: str) -> OnuState | None:
        return self._onus.get(serial.upper())

    async def deprovision(self, serial: str) -> bool:
        return self._onus.pop(serial.upper(), None) is not None

