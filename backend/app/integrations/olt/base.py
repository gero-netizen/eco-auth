from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class OnuState:
    serial: str
    status: str
    signal_dbm: float | None = None
    profile: str | None = None


class OltGateway(ABC):
    @abstractmethod
    async def discover(self) -> list[OnuState]: ...

    @abstractmethod
    async def provision(self, serial: str, profile: str) -> OnuState: ...

    @abstractmethod
    async def get_state(self, serial: str) -> OnuState | None: ...

    @abstractmethod
    async def deprovision(self, serial: str) -> bool: ...

