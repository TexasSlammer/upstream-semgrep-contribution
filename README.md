# Upstream Contribution: Semgrep `avoid-pyyaml-load` Detection Coverage

Closing verified false negatives in an established open-source security rule —
`python.lang.security.deserialization.avoid-pyyaml-load` in
[semgrep/semgrep-rules](https://github.com/semgrep/semgrep-rules) — with a
reproducible gap analysis, a hardened rule fix, regression tests, and a measured
zero-false-positive result.

## Results at a glance

| Metric | Result |
| --- | --- |
| Detection gap identified | 4 gap classes / 9 unreported call shapes (CWE-502 sink) |
| Probe corpus | 7 matches before → 17 after (**+10 detections — the 9 gap shapes + 1 documented edge case — 0 lost**) |
| Upstream test suite | Original rule **fails** the extended suite (8 missing findings); improved rule passes 100% |
| False-positive battery | **3,577 files / 6 established projects: 0 new false positives**, 0 lost findings |
| Rule schema | `semgrep validate`: 0 fatal errors |
| Baseline | semgrep 1.183.0 · semgrep-rules@`16b9e6d` (2026-10-21) · PyYAML 6.0.3 |

## The gap, in one minute

The rule flags unsafe PyYAML deserialization — `yaml.unsafe_load(...)`,
`yaml.load(..., Loader=yaml.Loader)`, etc. — a CWE-502 sink with a direct
arbitrary-code-execution path via YAML tags like `!!python/object/new:os.system`.
But PyYAML's documented signatures are `load(stream, Loader)` and
`load_all(stream, Loader)`, and the module also ships `unsafe_load_all(stream)`.
The rule's patterns only encode the **keyword** loader form and never mention
`unsafe_load_all`. Every one of the following executes the unsafe loader and was
reported by **zero** findings before this fix:

```python
import yaml
yaml.load(payload, yaml.UnsafeLoader)          # positional, module-qualified

from yaml import load, CLoader
load(payload, CLoader)                         # positional, from-imported name

import yaml
yaml.unsafe_load_all(payload)                  # API member absent from the rule
```

## Repository map

```
├── CASE-STUDY.md          # full technical write-up: gap → RCA → fix → measurement
├── WALKTHROUGH.md         # annotated rule + design-iteration log + Q&A prep
├── rule/
│   ├── avoid-pyyaml-load.yaml   # the improved rule (PR artifact)
│   └── avoid-pyyaml-load.py     # extended upstream test file (PR artifact)
├── reproduction/
│   ├── probes/                  # isolation-correct probe & guard corpus
│   ├── evidence-probe-corpus.txt
│   ├── guard-battery.txt
│   └── test-suite-differential.txt
├── measurement/
│   ├── measure_fp.py            # self-contained: rebuilds the FP table from scratch
│   ├── fp-scan-results.txt      # 6 repos / 3,577 files / delta = 0
│   └── delta_findings.json
└── upstream/
    ├── ISSUE.md                 # paste-ready upstream issue
    ├── PR_DESCRIPTION.md        # paste-ready PR text (incl. AI-assistance note)
    └── PUSH_GUIDE.md            # exact fork → branch → push → PR commands
```

## Verify everything yourself

```bash
pip install semgrep==1.183.0        # match the pinned version

# 1. the improved rule passes the extended upstream test suite
cd rule && semgrep test --config avoid-pyyaml-load.yaml avoid-pyyaml-load.py

# 2. the original rule fails it (tests actually detect the gap)
curl -sSL -o /tmp/orig.yaml \
  https://raw.githubusercontent.com/semgrep/semgrep-rules/16b9e6d45f10649f6a531ec4838ed9924372c3bc/python/lang/security/deserialization/avoid-pyyaml-load.yaml
SEMGREP_SEND_METRICS=off semgrep test --config /tmp/orig.yaml avoid-pyyaml-load.py

# 3. probe corpus: 7 → 17 matches, all true-negative guards silent
semgrep scan --config avoid-pyyaml-load.yaml --no-git-ignore --metrics=off ../reproduction/probes/

# 4. false-positive battery (clones 6 repos on first run, ~10 min)
cd ../measurement && python3 measure_fp.py
```

## Skills demonstrated

Security detection engineering: systematic detection-gap analysis against a
published tool version; false-negative taxonomy construction; rule engineering
with metavariable unification, import-context scoping, and regex guards;
regression-test design that provably detects the original defect; and
false-positive quantification across real-world code at scale.

## Provenance & tooling

Baseline rule fetched from semgrep-rules at commit `16b9e6d45f10649f6a531ec4838ed9924372c3bc`
(2026-10-21) and tested against semgrep 1.183.0 (PyPI) with PyYAML 6.0.3.
Developed with AI assistance (Z.ai); every claim,
number, and code path in this repository was produced and verified by
executing the commands shown above — see `WALKTHROUGH.md` for the full
decision log and the exact iteration history, including the false positives
caught and eliminated along the way.
