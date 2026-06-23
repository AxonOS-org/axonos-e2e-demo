# SPDX-License-Identifier: Apache-2.0 OR MIT
# Copyright (c) 2026 The AxonOS Project
"""
IntentObservation — the typed event that crosses the application boundary.

This is the SAME 32-byte little-endian wire record as the reference Rust SDK
(`axonos-sdk`) and the Python SDK (`axonos-sdk-python`):

| offset | size | field           |
|:-------|:-----|:----------------|
| 0      | 8    | timestamp_us  (u64) |
| 8      | 2    | kind_tag      (u16) |
| 10     | 2    | quality_raw   (u16, Q0.16; 65535 == 1.0) |
| 12     | 4    | payload       (bytes; byte 0 carries the typed value) |
| 16     | 8    | session_id    (u64) |
| 24     | 8    | attestation   (8-byte truncated HMAC-SHA256) |

Applications receive only this record. They never see the raw EEG.
"""
from __future__ import annotations

import hmac
import hashlib
from dataclasses import dataclass

WIRE_SIZE = 32
CONFIDENCE_DENOM = 65535
KERNEL_ABI_VERSION = 1

# kind tags (mirror axonos_sdk::intent::KindTag)
TAG_DIRECTION = 0x0001
TAG_LOAD = 0x0002
TAG_QUALITY = 0x0003

# enum values (mirror the Rust SDK)
DIRECTION = {"up": 0, "right": 1, "down": 2, "left": 3, "neutral": 4}
LOAD = {"low": 0, "moderate": 1, "high": 2}
QUALITY = {"high": 0, "moderate": 1, "low": 2, "no_signal": 3}

_TAG_NAME = {TAG_DIRECTION: "direction", TAG_LOAD: "load", TAG_QUALITY: "quality"}
_DIR_NAME = {v: k for k, v in DIRECTION.items()}
_LOAD_NAME = {v: k for k, v in LOAD.items()}
_QUAL_NAME = {v: k for k, v in QUALITY.items()}


@dataclass(frozen=True)
class IntentObservation:
    timestamp_us: int
    kind_tag: int
    quality_raw: int
    payload: bytes  # exactly 4 bytes
    session_id: int
    attestation: bytes  # exactly 8 bytes

    def to_wire(self) -> bytes:
        b = bytearray(WIRE_SIZE)
        b[0:8] = self.timestamp_us.to_bytes(8, "little")
        b[8:10] = self.kind_tag.to_bytes(2, "little")
        b[10:12] = self.quality_raw.to_bytes(2, "little")
        b[12:16] = self.payload[:4].ljust(4, b"\x00")
        b[16:24] = self.session_id.to_bytes(8, "little")
        b[24:32] = self.attestation[:8].ljust(8, b"\x00")
        return bytes(b)

    @classmethod
    def from_wire(cls, data: bytes) -> "IntentObservation":
        if len(data) != WIRE_SIZE:
            raise ValueError(f"wire record must be {WIRE_SIZE} bytes, got {len(data)}")
        return cls(
            timestamp_us=int.from_bytes(data[0:8], "little"),
            kind_tag=int.from_bytes(data[8:10], "little"),
            quality_raw=int.from_bytes(data[10:12], "little"),
            payload=bytes(data[12:16]),
            session_id=int.from_bytes(data[16:24], "little"),
            attestation=bytes(data[24:32]),
        )

    def kind(self) -> dict:
        """Decoded typed kind, as the SDK would expose it."""
        value = self.payload[0]
        if self.kind_tag == TAG_DIRECTION:
            return {"kind": "direction", "value": _DIR_NAME.get(value, "unknown")}
        if self.kind_tag == TAG_LOAD:
            return {"kind": "load", "value": _LOAD_NAME.get(value, "unknown")}
        if self.kind_tag == TAG_QUALITY:
            return {"kind": "quality", "value": _QUAL_NAME.get(value, "unknown")}
        return {"kind": "unknown", "value": value}

    def to_json(self) -> dict:
        k = self.kind()
        return {
            "timestamp_us": self.timestamp_us,
            "kind": k["kind"],
            "value": k["value"],
            "confidence_raw": self.quality_raw,
            "session_id": self.session_id,
            "attestation_hex": self.attestation.hex(),
        }


def attest(record_without_attestation: bytes, key: bytes) -> bytes:
    """8-byte truncated HMAC-SHA256 over the first 24 bytes (demo attestation).

    NOTE: this uses a DEMO key shipped in the repo. It proves the field is real
    and verifiable; it is not a production key-management scheme.
    """
    mac = hmac.new(key, record_without_attestation[:24], hashlib.sha256).digest()
    return mac[:8]


def build_observation(
    timestamp_us: int,
    kind_tag: int,
    value: int,
    confidence_raw: int,
    session_id: int,
    key: bytes,
) -> IntentObservation:
    payload = bytes([value & 0xFF, 0, 0, 0])
    head = bytearray(WIRE_SIZE)
    head[0:8] = timestamp_us.to_bytes(8, "little")
    head[8:10] = kind_tag.to_bytes(2, "little")
    head[10:12] = (confidence_raw & 0xFFFF).to_bytes(2, "little")
    head[12:16] = payload
    head[16:24] = session_id.to_bytes(8, "little")
    tag = attest(bytes(head), key)
    return IntentObservation(
        timestamp_us=timestamp_us,
        kind_tag=kind_tag,
        quality_raw=confidence_raw & 0xFFFF,
        payload=payload,
        session_id=session_id,
        attestation=tag,
    )
