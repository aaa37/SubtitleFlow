"""Future enhancement boundary; no entitlement checks or paid promises in v0.1."""
from typing import Protocol
from .subtitles import Segment


class SubtitleTransform(Protocol):
    def apply(self, segments: list[Segment]) -> list[Segment]: ...


class Entitlements(Protocol):
    def allows(self, feature: str) -> bool: ...


class BasicEdition:
    def allows(self, feature: str) -> bool:
        return feature in {"batch", "srt", "vtt", "txt", "editor"}
