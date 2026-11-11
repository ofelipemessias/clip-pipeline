from dataclasses import dataclass, field


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class Moment:
    start: float
    end: float
    reason: str = ""
    score: float = 0.0


@dataclass
class ClipResult:
    path: str
    moment: Moment
    captions_path: str = ""
    extras: dict = field(default_factory=dict)
