"""Shared result contract for per-item stage services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

StageItemStatus = Literal["processed", "failed", "skipped"]


@dataclass(frozen=True)
class StageItemResult:
    """Outcome returned by a per-item stage workflow."""

    status: StageItemStatus
    message: str | None = None

    @classmethod
    def processed(cls, message: str | None = None) -> StageItemResult:
        return cls(status="processed", message=message)

    @classmethod
    def failed(cls, message: str | None = None) -> StageItemResult:
        return cls(status="failed", message=message)

    @classmethod
    def skipped(cls, message: str | None = None) -> StageItemResult:
        return cls(status="skipped", message=message)

    @property
    def succeeded(self) -> bool:
        return self.status == "processed"
