#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (c) 2026 The AxonOS Project
"""
Generate the synthetic EEG fixture (deterministic, integer, cross-platform).

THIS IS SYNTHETIC DATA. It is not recorded from a person, not biologically
realistic, and carries no accuracy/latency/clinical meaning. It exists solely to
drive the end-to-end demo deterministically and to exercise every code path
(each gate, each consent transition).

Each 1-second window (250 samples @ 250 Hz, 8 channels) carries a single integer
square wave whose period is chosen so the pipeline's comb-filter energy peaks at
a known lag, which the demonstrator classifier maps to a known intent. A small
integer LCG adds deterministic "noise".
"""
from __future__ import annotations

import csv
import os
import sys

FS = 250          # Hz
WINDOW = 250      # samples per window (1 s)
CHANNELS = 8
AMP = 600         # square-wave amplitude (arbitrary integer units)
NOISE = 9         # +/- integer noise amplitude

# window index -> square-wave period (samples). period = 2*lag makes that lag
# dominant. None -> resting/neutral (tiny amplitude).
#   P2->Quality(low)  P4->Load(high)  P6->up  P10->right  P16->down  P26->left
WINDOW_PERIODS = [
    6,    # w0  up
    10,   # w1  right
    16,   # w2  down
    26,   # w3  left
    4,    # w4  Load(high)   -> dropped by capability gate
    6,    # w5  up           -> suppressed (consent Suspended)
    10,   # w6  right        -> emitted (consent Resumed)
    2,    # w7  Quality(low) -> dropped by capability gate
    16,   # w8  down
    26,   # w9  left
    6,    # w10 up           -> consent Withdrawn here; suppressed from now on
    10, 16, 26, 6, 10, 16, 26, 6, 10,   # w11..w19 all suppressed (terminal)
]
NUM_WINDOWS = len(WINDOW_PERIODS)  # 20


def lcg(state: int) -> int:
    # Numerical Recipes LCG, 32-bit; deterministic integer noise source
    return (1664525 * state + 1013904223) & 0xFFFFFFFF


def square(n: int, period: int, amp: int) -> int:
    return amp if (n % period) < (period // 2) else -amp


def generate_rows():
    rows = []
    rng = 0x1BADB002
    for w, period in enumerate(WINDOW_PERIODS):
        amp = AMP if period is not None else 0
        for s in range(WINDOW):
            n = w * WINDOW + s
            base = square(s, period, amp) if period else 0
            row = [n]
            for ch in range(CHANNELS):
                rng = lcg(rng)
                noise = (rng % (2 * NOISE + 1)) - NOISE
                row.append(base + noise)
            rows.append(row)
    return rows


def consent_events():
    # window_index, event
    return [(5, "suspend"), (6, "resume"), (10, "withdraw")]


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "fixtures"
    os.makedirs(out_dir, exist_ok=True)
    rows = generate_rows()
    trace_path = os.path.join(out_dir, "synthetic_trace.csv")
    with open(trace_path, "w", newline="") as f:
        wri = csv.writer(f)
        wri.writerow(["sample"] + [f"ch{c}" for c in range(CHANNELS)])
        wri.writerows(rows)
    ce_path = os.path.join(out_dir, "consent_events.csv")
    with open(ce_path, "w", newline="") as f:
        wri = csv.writer(f)
        wri.writerow(["window", "event"])
        for w, ev in consent_events():
            wri.writerow([w, ev])
    print(f"wrote {trace_path} ({len(rows)} samples, {CHANNELS} ch, {NUM_WINDOWS} windows)")
    print(f"wrote {ce_path}")


if __name__ == "__main__":
    main()
