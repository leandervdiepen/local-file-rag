"""A real, in-memory PowerSource. Not a mock."""

from __future__ import annotations


class FakePowerSource:
    def __init__(self, on_ac: bool = True) -> None:
        self.on_ac = on_ac

    def on_ac_power(self) -> bool:
        return self.on_ac
