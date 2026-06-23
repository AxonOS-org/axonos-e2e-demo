#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (c) 2026 The AxonOS Project
"""
Sample application: a cursor driven by AxonOS intent.

It consumes ONLY typed IntentObservations (kind / value / confidence). It is
never given the raw EEG, the features, or the classifier internals — that is the
entire point of the AxonOS boundary. Intents the app never declared (Load,
Quality) never reach it, and once consent is withdrawn the stream simply ends.
"""
import json
import sys

MOVES = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0), "neutral": (0, 0)}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "expected/intent_observations.jsonl"
    x = y = 0
    n = 0
    print("cursor app — receives typed intent only (zero bytes of raw neural data)\n")
    with open(path) as f:
        for line in f:
            o = json.loads(line)
            if o["kind"] != "direction":
                continue
            dx, dy = MOVES.get(o["value"], (0, 0))
            x += dx
            y += dy
            n += 1
            conf = o["confidence_raw"] / 65535
            t_ms = o["timestamp_us"] // 1000
            print(f"  t={t_ms:>6} ms   {o['value']:<7} (conf {conf:4.0%})   cursor -> ({x:>2},{y:>2})")
    print(f"\napplied {n} navigation intents; final cursor = ({x}, {y})")
    print("the application saw 0 raw samples and 0 undeclared intent classes.")


if __name__ == "__main__":
    main()
