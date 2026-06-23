# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (c) 2026 The AxonOS Project
"""
Capability / manifest gate — mirrors `axonos-sdk` manifest semantics.

An application declares the capabilities it is allowed to receive. The kernel
boundary drops any intent whose class is not declared. In this demo the sample
app declares only `navigation`, so Load / Quality intents are dropped at the
gate — the application literally cannot receive intent classes it never asked
for.
"""
from __future__ import annotations

from .intent import TAG_DIRECTION, TAG_LOAD, TAG_QUALITY

# capability -> the intent tag it authorises
NAVIGATION = "navigation"
WORKLOAD_ADVISORY = "workload_advisory"
SESSION_QUALITY = "session_quality"

_CAP_FOR_TAG = {
    TAG_DIRECTION: NAVIGATION,
    TAG_LOAD: WORKLOAD_ADVISORY,
    TAG_QUALITY: SESSION_QUALITY,
}

# kernel-enforced per-capability rate ceilings (Hz), mirror the SDK
KERNEL_RATE_LIMIT_HZ = {
    NAVIGATION: 50,
    WORKLOAD_ADVISORY: 1,
    SESSION_QUALITY: 2,
}


class Manifest:
    def __init__(self, app_id: str, capabilities, max_rate_hz: int):
        if not app_id or len(app_id.encode()) > 64:
            raise ValueError("app_id must be non-empty and <= 64 bytes")
        caps = list(dict.fromkeys(capabilities))
        if not caps:
            raise ValueError("manifest must declare at least one capability")
        if max_rate_hz <= 0:
            raise ValueError("max_rate_hz must be > 0")
        min_limit = min(KERNEL_RATE_LIMIT_HZ[c] for c in caps)
        if max_rate_hz > min_limit:
            raise ValueError(f"max_rate_hz {max_rate_hz} exceeds kernel limit {min_limit}")
        self.app_id = app_id
        self.capabilities = caps
        self.max_rate_hz = max_rate_hz

    def allows_tag(self, kind_tag: int) -> bool:
        cap = _CAP_FOR_TAG.get(kind_tag)
        return cap is not None and cap in self.capabilities
