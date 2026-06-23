#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (c) 2026 The AxonOS Project
"""
End-to-end runner. Wires the canonical AxonOS boundary, in software, on
synthetic data:

    synthetic EEG window
        -> signal pipeline (band energies)
        -> classifier decision (typed intent + confidence)
        -> consent gate  (Granted only; Withdrawn is terminal)
        -> capability gate (manifest declares Navigation only)
        -> IntentObservation (32-byte wire record, attested)
        -> sample app receives typed intent (never the raw EEG)

Output is deterministic: same fixtures -> identical wire records -> identical
hashes, on any platform. Run with:

    PYTHONPATH=src python3 -m axonos_e2e.runner fixtures expected
"""
from __future__ import annotations

import csv
import json
import os
import sys

from .pipeline import window_features
from .classifier import classify
from .consent import Consent, GRANTED
from .manifest import Manifest, NAVIGATION
from .intent import build_observation, IntentObservation

WINDOW = 250
WINDOW_DUR_US = 1_000_000          # 250 samples @ 250 Hz = 1.0 s
SESSION_ID = 0xA000000000000001    # fixed demo session
DEMO_KEY = b"axonos-e2e-demo/attestation-key/v1"   # DEMO key (see README)


def load_trace(path):
    rows = []
    with open(path) as f:
        r = csv.reader(f)
        next(r)  # header
        for line in r:
            rows.append([int(x) for x in line[1:]])  # drop the sample index column
    return rows


def load_consent_events(path):
    ev = {}
    with open(path) as f:
        r = csv.reader(f)
        next(r)
        for line in r:
            ev[int(line[0])] = line[1].strip()
    return ev


def run(fixtures_dir: str, out_dir: str) -> dict:
    rows = load_trace(os.path.join(fixtures_dir, "synthetic_trace.csv"))
    events = load_consent_events(os.path.join(fixtures_dir, "consent_events.csv"))

    # the sample app asks for navigation only
    manifest = Manifest("org.axonos.demo.cursor", [NAVIGATION], max_rate_hz=50)
    consent = Consent(GRANTED)

    n_windows = len(rows) // WINDOW
    emitted_hex, emitted_json, decisions, transitions = [], [], [], []
    n_emitted = n_drop_cap = n_supp_consent = 0

    for w in range(n_windows):
        if w in events:
            before = consent.state
            after = consent.apply(events[w])
            transitions.append({"window": w, "event": events[w], "from": before, "to": after})

        window = rows[w * WINDOW:(w + 1) * WINDOW]
        energies = window_features(window)
        tag, value, conf = classify(energies)

        probe = IntentObservation(0, tag, conf, bytes([value, 0, 0, 0]), 0, b"\x00" * 8).kind()
        dec = {
            "window": w, "kind": probe["kind"], "value": probe["value"],
            "confidence_raw": conf, "consent": consent.state,
        }

        # ── consent gate: only Granted emits; Withdrawn is terminal ──
        if not consent.emits():
            dec["outcome"] = "suppressed_consent"
            n_supp_consent += 1
            decisions.append(dec)
            continue
        # ── capability gate: drop intent classes the manifest never declared ──
        if not manifest.allows_tag(tag):
            dec["outcome"] = "dropped_capability"
            n_drop_cap += 1
            decisions.append(dec)
            continue

        ts = w * WINDOW_DUR_US
        obs = build_observation(ts, tag, value, conf, SESSION_ID, DEMO_KEY)
        emitted_hex.append(obs.to_wire().hex())
        emitted_json.append(obs.to_json())
        dec["outcome"] = "emitted"
        n_emitted += 1
        decisions.append(dec)

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "intent_observations.jsonl"), "w") as f:
        for j in emitted_json:
            f.write(json.dumps(j, separators=(",", ":"), sort_keys=True) + "\n")
    with open(os.path.join(out_dir, "intent_observations.hex"), "w") as f:
        for h in emitted_hex:
            f.write(h + "\n")
    with open(os.path.join(out_dir, "decisions.jsonl"), "w") as f:
        for d in decisions:
            f.write(json.dumps(d, separators=(",", ":"), sort_keys=True) + "\n")

    summary = {
        "windows": n_windows,
        "emitted": n_emitted,
        "dropped_capability": n_drop_cap,
        "suppressed_consent": n_supp_consent,
        "consent_transitions": transitions,
        "final_consent_state": consent.state,
        "manifest": {
            "app_id": manifest.app_id,
            "capabilities": manifest.capabilities,
            "max_rate_hz": manifest.max_rate_hz,
        },
        "abi_version": 1,
        "wire_size_bytes": 32,
    }
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
    return summary


def main():
    fixtures_dir = sys.argv[1] if len(sys.argv) > 1 else "fixtures"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "expected"
    s = run(fixtures_dir, out_dir)
    print(json.dumps(s, indent=2))


if __name__ == "__main__":
    main()
