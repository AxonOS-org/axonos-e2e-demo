# axonos-e2e-demo

[![AxonOS Radar](https://img.shields.io/badge/AxonOS%20Radar-open%20neurotech%20map-1f8fae?style=flat-square&labelColor=0b1220)](https://axonos-bci.github.io/axonos-community-radar/)

**A reproducible, end-to-end AxonOS intent flow — synthetic signal in, typed consent-bound intent out.**

This repository answers one diligence question directly: *can AxonOS show a complete, reproducible path from a signal frame to a typed intent event an application can consume, with the consent and capability boundary actually enforced?* It runs that whole path in software, on clearly-labelled synthetic data, and verifies the output bit-for-bit on every run.

```text
synthetic EEG window
    ──▶ signal pipeline        (integer comb-filter band energies)
    ──▶ classifier decision    (typed intent + integer confidence)
    ──▶ consent gate           (Granted only; Withdrawn is terminal)
    ──▶ capability gate        (manifest declares "navigation" only)
    ──▶ IntentObservation      (32-byte attested wire record)
    ──▶ sample app             (receives typed intent — never the raw EEG)
```

## Scope and honesty

Read this before drawing any conclusion from the numbers here.

- **Synthetic data.** The input is generated integer waveforms, not recorded neural signals. See [`fixtures/SYNTHETIC.md`](fixtures/SYNTHETIC.md).
- **Demonstrator classifier.** A transparent, rule-based argmax over band energies. It was **not** trained and makes **no accuracy claim**.
- **Software only.** This is a functional/integration demonstrator. It measures **no** latency, throughput, jitter, or power, and runs on no special hardware.
- **Not a medical device.** No clinical claim of any kind.

What it *does* establish, and all it claims to:

1. **The boundary is real.** The application receives only `IntentObservation` records — the same 32-byte wire format as the [Rust](https://github.com/AxonOS-org/axonos-sdk) and [Python](https://github.com/AxonOS-org/axonos-sdk-python) SDKs. It never receives raw samples, features, or classifier internals.
2. **Capability gating works.** The sample app's manifest declares only `navigation`, so `Load` and `Quality` intents are dropped at the gate and never reach it.
3. **Consent is enforceable and terminal.** A `suspend` pauses emission; a `resume` restores it; a `withdraw` is terminal — once withdrawn, no further intent crosses the boundary for the rest of the run.
4. **It is reproducible.** Everything is exact integer arithmetic, so the same fixtures produce byte-identical wire records and hashes on any platform. `./run.sh --verify` proves it, and CI runs that gate on every push.

### Evidence level

Using the AxonOS evidence ladder (`L0` target · `L1` bounded/formal/deterministic · `L2` measured lab · `L3` independent external · `L4` clinical/regulatory):

> This demo is **L1**: it demonstrates functional correctness and deterministic reproduction of the boundary on synthetic data. It is **not** L2 (no measured performance), L3 (no external review), or L4 (no clinical evidence). Measured figures, when they exist, live only in [`axonos-validation`](https://github.com/AxonOS-org/axonos-validation).

## Run it

```bash
./run.sh                 # build fixtures + expected outputs + SHA256SUMS
./run.sh --verify        # regenerate everything and prove it matches, bit-for-bit
python3 examples/cursor_app.py expected/intent_observations.jsonl
```

No dependencies beyond Python 3.9+. Nothing is fetched; nothing leaves the machine.

### What you will see

The run classifies 20 one-second windows and reports:

```
windows: 20 · emitted: 7 · dropped_capability: 2 · suppressed_consent: 11
consent: Granted → Suspended (w5) → Granted (w6) → Withdrawn (w10, terminal)
```

The sample app then turns those 7 emitted navigation intents into cursor moves. The gaps in its timeline (a dropped `Load`, a suspended window, a dropped `Quality`, then the terminal withdrawal) are the gates doing their job — visible from the application side without the application ever seeing why.

## Layout

| Path | What |
|:--|:--|
| `src/axonos_e2e/intent.py` | `IntentObservation` 32-byte wire codec + HMAC attestation |
| `src/axonos_e2e/pipeline.py` | Deterministic integer band-energy features |
| `src/axonos_e2e/classifier.py` | Rule-based demonstrator classifier |
| `src/axonos_e2e/consent.py` | Consent FSM (Granted / Suspended / Withdrawn-terminal) |
| `src/axonos_e2e/manifest.py` | Capability / manifest gate |
| `src/axonos_e2e/runner.py` | Wires the full boundary end to end |
| `scripts/gen_fixture.py` | Deterministic synthetic-EEG generator |
| `examples/cursor_app.py` | Sample app — consumes typed intent only |
| `fixtures/` | Synthetic input (labelled) |
| `expected/` | Golden outputs: `intent_observations.{jsonl,hex}`, `decisions.jsonl`, `summary.json` |
| `SHA256SUMS` | Hashes of every fixture and golden output |

## The attestation key

`IntentObservation.attestation` is a real 8-byte truncated HMAC-SHA256 over the record, computed with a **demo key committed in this repository** (`src/axonos_e2e/intent.py`). It proves the field is genuine and verifiable; it is **not** a production key-management scheme.

## Relationship to the rest of AxonOS

This is a **reference demonstrator**, not the product. The real components live under [AxonOS-org](https://github.com/AxonOS-org): the standard and canonical claims (`axonos-standard`), the kernel substrate (`axonos-kernel`), the consent FSM (`axonos-consent`), the signal pipeline (`axonos-signal-pipeline`), the SDKs, and measured traces (`axonos-validation`). This repo simply stitches the boundary together so the whole path can be seen, run, and reproduced in one command.

## License

Licensed under either of [Apache-2.0](LICENSE-APACHE) or [MIT](LICENSE-MIT) at your option.

---

<div align="center">
<sub><b>The AxonOS Project</b> · <a href="https://axonos.org">axonos.org</a> · connect@axonos.org · security@axonos.org</sub>
</div>
