# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (c) 2026 The AxonOS Project
"""
Consent finite-state machine — mirrors `axonos-consent`.

States: Granted, Suspended, Withdrawn. `Withdrawn` is TERMINAL: once consent is
withdrawn, no further intent may cross the boundary, ever, unless a new signed
grant is issued (out of scope for this demo). This is the core safety property
the demo exists to show: the boundary can be closed irreversibly.

Only `Granted` permits emission. `Suspended` pauses emission (reversible).
"""
from __future__ import annotations

GRANTED = "Granted"
SUSPENDED = "Suspended"
WITHDRAWN = "Withdrawn"


class ConsentError(Exception):
    pass


class Consent:
    def __init__(self, state: str = GRANTED):
        self._state = state

    @property
    def state(self) -> str:
        return self._state

    def emits(self) -> bool:
        """True only while consent is Granted."""
        return self._state == GRANTED

    def apply(self, event: str) -> str:
        """Apply a consent event. Returns the new state.

        Transitions:
          grant   : Suspended -> Granted        (no-op if already Granted; refused if Withdrawn)
          suspend : Granted   -> Suspended
          resume  : Suspended -> Granted
          withdraw: any non-terminal -> Withdrawn (terminal)
        """
        ev = event.strip().lower()
        if self._state == WITHDRAWN:
            # terminal: nothing reactivates it in this demo
            if ev == "withdraw":
                return self._state
            raise ConsentError(f"consent is Withdrawn (terminal); '{ev}' refused")
        if ev == "withdraw":
            self._state = WITHDRAWN
        elif ev == "suspend":
            if self._state == GRANTED:
                self._state = SUSPENDED
        elif ev in ("resume", "grant"):
            if self._state == SUSPENDED:
                self._state = GRANTED
        else:
            raise ConsentError(f"unknown consent event: '{ev}'")
        return self._state
