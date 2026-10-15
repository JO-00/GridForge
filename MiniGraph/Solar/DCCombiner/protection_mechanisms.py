
from dataclasses import dataclass
from enum import Enum, auto
import json


@dataclass
class DCBusbar:
    voltage_v: float = 0.0
    current_a: float = 0.0


class SPDState(Enum):
    HEALTHY = auto()
    CONDUCTING = auto()
    FAILED = auto()


@dataclass
class SurgeProtectionDevice:
    clamp_SPD_voltage : float
    surge_threshold_v: float
    state: SPDState = SPDState.HEALTHY
    surge_events: int = 0

    def __post_init__(self) -> None:
        if self.surge_threshold_v <= 0:
            raise ValueError("Surge threshold must be positive.")

    def step(self, observed_voltage_v: float) -> None:
        if self.state == SPDState.FAILED:
            return

        if observed_voltage_v > self.surge_threshold_v:
            if self.state != SPDState.CONDUCTING:
                self.surge_events += 1

            self.state = SPDState.CONDUCTING
        else:
            self.state = SPDState.HEALTHY

    def fail(self) -> None:
        self.state = SPDState.FAILED

    def replace(self) -> None:
        self.state = SPDState.HEALTHY
