# Phase 11: Advanced Config Tuning - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-08
**Phase:** 11-advanced-config-tuning
**Areas discussed:** Testing strategy, PSM 7 feasibility, Revert granularity, Stop condition

---

## Testing Strategy

### How should configs be tested?

| Option | Description | Selected |
|--------|-------------|----------|
| Independent + combos | Test each config in isolation first, then test winning combination. Catches interactions. | ✓ |
| Independent only | Test each in isolation. Apply all that pass. Simpler but misses interaction effects. | |
| Cumulative stacking | Apply one, benchmark, add next on top. Faster but can't isolate regressions. | |

**User's choice:** Independent + combos
**Notes:** None

### Extend benchmark.py or new script?

| Option | Description | Selected |
|--------|-------------|----------|
| Extend benchmark.py | Add benchmark_tesseract_config() to existing script. Reuses infrastructure. | ✓ |
| New script | Create tesseract_benchmark.py separately. Keeps Phase 10 and 11 independent. | |

**User's choice:** Extend benchmark.py
**Notes:** None

### Accuracy baseline for Phase 11?

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 10 results (DPI 200) | Compare against current pipeline state. Regressions from HERE matter. | ✓ |
| v1.1 original baseline | Compare against original v1.1. More conservative, ensures no cumulative drift. | |

**User's choice:** Phase 10 results (DPI 200)
**Notes:** None

---

## PSM 7 Feasibility

### How to approach PSM 7 testing?

| Option | Description | Selected |
|--------|-------------|----------|
| Try on full page first | Just swap PSM 6 to PSM 7 and benchmark. If accuracy holds, no extra complexity. | ✓ |
| Crop ID region first | Detect and crop Precede ID region before OCR. More reliable for PSM 7 but adds complexity. | |
| Test both approaches | Benchmark PSM 7 on full pages AND on cropped regions. Most thorough but doubles work. | |

**User's choice:** Try on full page first
**Notes:** None

### PSM fallback if PSM 7 fails?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep PSM 6 | PSM 6 is proven at 94.9%. If PSM 7 fails, don't chase other PSMs — move on. | ✓ |
| Try PSM 13 too | PSM 13 (raw line) might work where PSM 7 doesn't. Worth one extra benchmark. | |

**User's choice:** Keep PSM 6
**Notes:** None

---

## Revert Granularity

### Partial wins policy?

| Option | Description | Selected |
|--------|-------------|----------|
| Apply any that pass | Each config that passes accuracy gets applied. Ship partial wins. | ✓ |
| All or nothing | Only apply if all three pass. If any fails, revert everything. | |

**User's choice:** Apply any that pass
**Notes:** None

### Accuracy threshold strictness?

| Option | Description | Selected |
|--------|-------------|----------|
| Hard 94% cutoff | 94.0% or above passes. 93.9% fails. No exceptions. | |
| Soft margin (93-94%) | Allow 93-94% if speed gain is substantial. Report tradeoff, user decides. | ✓ |
| Round to nearest % | >=93.5% rounds to 94% and passes. Below 93.5% fails. | |

**User's choice:** Soft margin (93-94%)
**Notes:** User wants to see the tradeoff for borderline cases rather than hard-reject

---

## Stop Condition

### What if combined speedup is <1.5x?

| Option | Description | Selected |
|--------|-------------|----------|
| Ship any improvement | Even 1.1x is free speed. Config changes have zero code complexity cost. | ✓ |
| Stick to 1.5x threshold | If <1.5x combined, revert everything. Not worth the testing overhead. | |
| Ship but skip Phase 12 | Apply whatever wins, but <1.5x signals diminishing returns — skip Phase 12. | |

**User's choice:** Ship any improvement
**Notes:** None

### Phase 12 gate?

| Option | Description | Selected |
|--------|-------------|----------|
| Total runtime check | If Phases 10+11 get 30K corpus under 24 hours, Phase 12 unnecessary. | ✓ |
| Always do Phase 12 | Algorithmic improvements worth doing regardless of speed. | |
| Decide after benchmarks | No commitment — see Phase 11 results first. | |

**User's choice:** Total runtime check
**Notes:** 24-hour threshold for 30K corpus determines whether Phase 12 proceeds

---

## Claude's Discretion

- Order of testing configs
- Benchmark output format
- Combination testing structure
- Initial screening sample size

## Deferred Ideas

None — discussion stayed within phase scope
