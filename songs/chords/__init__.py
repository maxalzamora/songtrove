"""Music theory helpers used by the song library."""

from .capo import CapoPlan, plan_for, sounding_key_for, suggest_capos, written_key_for
from .parser import Line, LineKind, Segment, parse_line, parse_sheet
from .theory import KEY_CHOICES, pitch_of, spell
from .transpose import parse_chord, transpose_chord, transpose_key

__all__ = [
    "KEY_CHOICES",
    "CapoPlan",
    "Line",
    "LineKind",
    "Segment",
    "parse_chord",
    "parse_line",
    "parse_sheet",
    "pitch_of",
    "plan_for",
    "sounding_key_for",
    "spell",
    "suggest_capos",
    "transpose_chord",
    "transpose_key",
    "written_key_for",
]
