"""Typed errors used across the conversion pipeline."""

from __future__ import annotations


class Chart2SusError(Exception):
    """Base error for llll_chart2sus."""


class LoaderError(Chart2SusError):
    """Raised when source chart loading fails."""


class UnsupportedMappingError(Chart2SusError):
    """Raised when a note or feature is not yet mapped to SUS."""

    def __init__(self, note_uid: int, note_timing: float, note_type: str, reason: str):
        self.note_uid = note_uid
        self.note_timing = note_timing
        self.note_type = note_type
        self.reason = reason
        super().__init__(self.__str__())

    def __str__(self) -> str:
        return (
            f"Unsupported note mapping: uid={self.note_uid}, timing={self.note_timing:.6f}, "
            f"type={self.note_type}. {self.reason}"
        )


class ValidationError(Chart2SusError):
    """Raised when external validators fail."""


class ToolchainError(Chart2SusError):
    """Raised when required tools are not available."""

