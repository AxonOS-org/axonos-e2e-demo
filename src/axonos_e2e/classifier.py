# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (c) 2026 The AxonOS Project
"""
Deterministic demonstrator classifier.

Maps the integer band-energy vector to a typed intent. The decision is the
argmax band, mapped through a fixed table; confidence is the integer ratio of
the dominant band to the total, expressed as a u16 (Q0.16). This is a
transparent, rule-based demonstrator — it makes NO accuracy claim and was not
trained on any data.
"""
from __future__ import annotations

from typing import List, Tuple

from .intent import (
    TAG_DIRECTION,
    TAG_LOAD,
    TAG_QUALITY,
    DIRECTION,
    LOAD,
    QUALITY,
)
from .pipeline import LAGS

# argmax lag -> (kind_tag, value)
_LAG_TO_INTENT = {
    1: (TAG_QUALITY, QUALITY["low"]),
    2: (TAG_LOAD, LOAD["high"]),
    3: (TAG_DIRECTION, DIRECTION["up"]),
    5: (TAG_DIRECTION, DIRECTION["right"]),
    8: (TAG_DIRECTION, DIRECTION["down"]),
    13: (TAG_DIRECTION, DIRECTION["left"]),
}

# total energy below this -> treat the window as resting / neutral
NEUTRAL_ENERGY_THRESHOLD = 5_000_000


def classify(energies: List[int]) -> Tuple[int, int, int]:
    """Return (kind_tag, value, confidence_raw) for a band-energy vector."""
    total = sum(energies)
    if total < NEUTRAL_ENERGY_THRESHOLD:
        return TAG_DIRECTION, DIRECTION["neutral"], 0
    best_i = 0
    for i in range(1, len(energies)):
        if energies[i] > energies[best_i]:
            best_i = i
    lag = LAGS[best_i]
    tag, value = _LAG_TO_INTENT[lag]
    confidence_raw = (energies[best_i] * 65535) // total
    return tag, value, confidence_raw
