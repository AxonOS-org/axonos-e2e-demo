# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (c) 2026 The AxonOS Project
"""
Deterministic signal pipeline — mirrors the posture of `axonos-signal-pipeline`
(integer, dependency-free, no medical/accuracy claim).

It turns a window of raw multi-channel samples into a small vector of integer
"band energies" using comb-filter differences. For a comb (1 - z^-lag), the
differenced energy peaks when `lag` is half the dominant period of the signal,
so the energy vector encodes which rhythm dominates the window. Everything is
exact integer arithmetic, so the output is bit-identical on every platform.

This is an engineering demonstrator, NOT a clinically meaningful feature set.
"""
from __future__ import annotations

from typing import List

# comb lags probed per window (a small Fibonacci-spaced set)
LAGS = (1, 2, 3, 5, 8, 13)


def window_features(window_rows: List[List[int]]) -> List[int]:
    """Integer band energy per lag, summed across channels.

    `window_rows`: list of N samples; each sample is a list of C integer channels.
    Returns a list of len(LAGS) non-negative integers.
    """
    n = len(window_rows)
    if n == 0:
        return [0] * len(LAGS)
    c = len(window_rows[0])
    energies: List[int] = []
    for lag in LAGS:
        e = 0
        for ch in range(c):
            for i in range(lag, n):
                d = window_rows[i][ch] - window_rows[i - lag][ch]
                e += d * d
        energies.append(e)
    return energies
