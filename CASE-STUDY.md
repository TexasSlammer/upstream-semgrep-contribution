# Case Study: Closing Verified False Negatives in Semgrep's PyYAML Deserialization Rule

**Rule:** `python.lang.security.deserialization.avoid-pyyaml-load`
**Repository:** [semgrep/semgrep-rules](https://github.com/semgrep/semgrep-rules)
**Baseline:** rule at commit `16b9e6d45f10649f6a531ec4838ed9924372c3bc` (2026-10-21), tested with semgrep 1.183.0 (PyPI), PyYAML 6.0.3
**Outcome:** 9 previously-unreported call shapes of a CWE-502 sink now detected (probe corpus: 7 matches before → 17 after, 0 lost); 0 new false positives across 3,577 files in 6 established projects; upstream test suite extended with 8 true positives and 6 true negatives.

---

## 1. Executive summary

Semgrep's `avoid-pyyaml-load` rule guards against unsafe PyYAML deserialization
(`yaml.unsafe_load`, `yaml.load` with an unsafe `Loader`) — a CWE-502 sink with
a direct arbitrary-code-execution path through YAML tags such as
`!!python/object/new:os.system`. Auditing the rule's pattern grammar against
PyYAML 6.0.3's *actual* API surface revealed that three families of
RCE-equivalent call shapes fall outside the rule's coverage:

1. **`yaml.unsafe_load_all(...)`** — an API member the rule never mentions, which
   applies `UnsafeLoader` to every document in a stream.
2. **Positional loader arguments** — every `yaml.load`/`yaml.load_all` pattern in
   the rule hardcodes the `Loader=` keyword form, but PyYAML's signature is
   `load(stream, Loader)`, and the positional form is legal and identical in
   effect.
3. **Positional bare-name loaders via from-imports** —
   `from yaml import CLoader; load(data, CLoader)` combines both problems.

This document walks through how the gap was found, why the rule misses each
shape (root cause), how the fix was engineered (including two false-positive
introductions that were caught and eliminated during iteration), how the
regression tests prove the fix, and how the false-positive impact was measured
to zero across real-world code.

## 2. Background: the sink and the API surface

PyYAML is the dominant YAML parser in the Python ecosystem. Its `load()` family
constructs arbitrary Python objects when driven by an unsafe loader: a YAML
document containing `!!python/object/new:os.system ["id"]` executes `os.system`
at parse time. CVE-2017-18342 is the canonical reference. The PyYAML
maintainers' deprecation note (linked in the rule's own `references` metadata)
formalizes the loader model:

- **Unsafe by design:** `yaml.Loader`, `yaml.UnsafeLoader`, `yaml.CLoader`
  (constructs arbitrary objects), plus the convenience wrappers
  `yaml.unsafe_load` and `yaml.unsafe_load_all`.
- **Safe:** `yaml.SafeLoader`, `yaml.CSafeLoader`, `yaml.BaseLoader` and the
  `yaml.safe_load` / `yaml.safe_load_all` wrappers.
- **Intermediate:** `yaml.FullLoader` — restricted, with historical bypasses
  (CVE-2020-14343, fixed in PyYAML 5.4), deliberately *not* flagged by this
  rule (see §9).

The signatures were verified against the installed PyYAML 6.0.3:

```
load(stream, Loader)            # keyword-optional second parameter
load_all(stream, Loader)
unsafe_load_all(stream)         # UnsafeLoader applied internally, per-document
```

Two facts matter for detection engineering: the loader argument is
**positional-legal**, and `unsafe_load_all` is a **first-class public API
member** — not an exotic internal.

## 3. Methodology

The audit treated the rule as a *specification* and enumerated the observable
call surface it claims to cover:

1. **Extract the covered set** — read `avoid-pyyaml-load.yaml` and list every
   encoded call shape (7 `pattern-either` branches at baseline, all keyword-form).
2. **Enumerate the true sink set** — from PyYAML's public API: which
   call expressions hand an unsafe loader to a parsing entry point?
3. **Diff the sets**, then **prove each diff empirically** — every hypothesized
   miss was written as a minimal Python probe file and scanned with the
   *unmodified* baseline rule on semgrep 1.183.0. No claim enters this study
   that did not produce an empty result set on the baseline rule.
4. **Guard the fix** — for every new pattern branch, construct adversarial
   true-negative cases (safe loaders in the same syntactic position, local
   classes that shadow loader names, same-named APIs from unrelated modules)
   and require silence.

A deliberate methodological note: several intuitive "gaps" turned out to be
**already covered** by semgrep's engine, not the rule. `from yaml import
unsafe_load; unsafe_load(x)` and `import yaml as y; y.unsafe_load(x)` both
match the baseline rule because the engine resolves from-import callees and
module aliases (`y` → `yaml`) against patterns written in module-qualified
form. The resolution is module-aware: `from mypackage import unsafe_load;
unsafe_load(x)` correctly does **not** match. Detection engineers who assume
the older "community rules must enumerate import styles" folklore would have
added redundant branches; empirical probing prevented that.

## 4. The gap taxonomy (with proof)

All shapes below were verified missed by the baseline rule (empty result set)
and detected by the fixed rule. Probe files live in `reproduction/probes/`;
machine-readable evidence in `reproduction/evidence-probe-corpus.txt`.

| ID | Shape | Example | Probe |
| --- | --- | --- | --- |
| G1a | `yaml.unsafe_load_all(...)` | `yaml.unsafe_load_all(payload)` | gap-classes-2.py:5 |
| G1b | from-imported `unsafe_load_all` | `from yaml import unsafe_load_all; unsafe_load_all(payload)` | gap-classes-2.py:9 |
| G2a | positional `yaml.Loader` | `yaml.load(data, yaml.Loader)` | gap-classes-1.py:29 |
| G2b | positional `yaml.UnsafeLoader` | `yaml.load(data, yaml.UnsafeLoader)` | gap-classes-2.py:13 |
| G2c | positional `yaml.CLoader` on `load_all` | `yaml.load_all(data, yaml.CLoader)` | gap-classes-1.py:33 |
| G3a | positional bare name, single-name from-import | `from yaml import CLoader; yaml.load(data, CLoader)` | gap-classes-2.py:18, tp-from-import-positional.py:2 |
| G3b | positional bare name via `load` from-import | `from yaml import load; from yaml import UnsafeLoader; load(data, UnsafeLoader)` | (subsumed by G3a branch) |
| G4a | positional bare name, multi-name from-import | `from yaml import load, UnsafeLoader; load(data, UnsafeLoader)` | tp-multi-name-from-import.py:2 |
| G4b | multi-name from-import shadow-guarded | `from yaml import load, CLoader; load(data, CLoader)` with a local class defined earlier in file | edge-cases.py:3 |

Baseline rule on the full probe corpus: **7 matches** (6 expected true
positives already covered + 1 positive control). Fixed rule: **17 matches**
(+10: the 9 gap shapes above plus the documented edge-behavior case
`edge-call-before-shadow.py`, 0 lost). Two additional probe files document
non-detection behavior: `edge-alias-from-import-residual.py` (aliased
from-import — verified residual miss, see §10) and the true-negative guards
(`tn-*.py`, required to stay silent).

## 5. Root-cause analysis

Why does the baseline rule miss these shapes? Three independent causes, all in
the rule's pattern grammar rather than the engine:

**Cause 1 — keyword-only loader encoding.** Every loader-bearing branch is
written as `yaml.load(..., Loader=yaml.Loader, ...)`. Semgrep patterns match
syntactic argument structure; `Loader=` in the pattern binds a *keyword*
argument. The positional form `yaml.load(data, yaml.Loader)` has a different
AST shape (a second positional expression) and cannot match a keyword pattern.
The rule was written in 2020 when keyword form was the documented
recommendation; the positional convention (`load(stream, Loader)`) has always
been legal and remains common in older and audit-grade code.

**Cause 2 — incomplete API enumeration.** The rule covers `unsafe_load` but not
`unsafe_load_all`, although both are public module-level wrappers over the same
unsafe loader and `unsafe_load_all` has existed in the API since the wrapper
family was introduced. Nothing in the rule's structure prevents adding it —
it is a one-line omission, the same class of omission as #1135 (which added
multi-argument handling) and #2178 (which excluded `BaseLoader` after #2143
reported that false positive) in the repo's history.

**Cause 3 — no positional coverage for from-imported names.** Even granting
the engine's from-import callee resolution, the *argument* side is not
normalized: in `from yaml import CLoader; yaml.load(data, CLoader)`, the call
matches `yaml.load(..., $LOADER)` with `$LOADER` bound to the bare text
`CLoader` (not `yaml.CLoader`). No baseline branch existed for positional
arguments at all, so the bare-name case had no path to a match.

## 6. The fix

Five branches added to the existing `pattern-either` (full annotated
walk-through in `WALKTHROUGH.md`):

```yaml
# unsafe_load_all: same unsafe loader as unsafe_load, stream form
- pattern: yaml.unsafe_load_all(...)

# positional loader, module-qualified: regex restricts to the three unsafe classes
- patterns:
  - pattern: yaml.load(..., $LOADER)
  - metavariable-regex:
      metavariable: $LOADER
      regex: ^yaml\.(Loader|UnsafeLoader|CLoader)$
# ... and the same for yaml.load_all

# positional bare name: metavariable unification between the from-import
# statement and the call site, plus an unsafe-name regex and a local-class
# shadow exclusion
- patterns:
  - pattern-inside: |
      from yaml import $LOADER
      ...
  - pattern: yaml.load(..., $LOADER)
  - metavariable-regex:
      metavariable: $LOADER
      regex: ^(Loader|UnsafeLoader|CLoader)$
  - pattern-not-inside: |
      class $LOADER(...):
        ...
      ...
# ... and the same for yaml.load_all
```

Design rationale, condensed:

- **`unsafe_load_all` needs no loader argument** — it binds `UnsafeLoader`
  internally, so a plain call pattern suffices; the engine's from-import and
  alias resolution extends it to `from yaml import unsafe_load_all` for free.
- **Positional module-qualified form** uses `metavariable-regex` rather than
  three duplicated patterns. The regex is anchored (`^...$`) and restricted to
  exactly the three unsafe loader classes, so `yaml.load(data, yaml.SafeLoader)`
  — the critical true-negative — cannot match.
- **Positional bare-name form** is the subtle one. The naive approach (regex on
  the bare name alone) false-positives on local safe classes named `Loader`.
  The fix binds `$LOADER` in a `pattern-inside` over `from yaml import $LOADER`
  and lets metavariable **unification** require that the *same* name is
  imported from `yaml` and passed positionally. A `metavariable-regex` then
  restricts to the three unsafe names, and a `pattern-not-inside` over
  `class $LOADER(...)` excludes files where a local class shadows the imported
  name (semgrep binds sequence patterns greedily, so this guard is required for
  multi-class files).

## 7. Iteration log: two false positives caught and eliminated

Recorded because the negative results are the interesting part:

1. **Attempt 1 — `$ANY` import guard.** Positional bare-name branch guarded by
   `pattern-inside: from yaml import $ANY`. Caught by the adversarial corpus:
   a file with `from yaml import safe_load` (any from-import) plus a local
   `class CLoader(yaml.SafeLoader)` produced a **false positive** on
   `yaml.load(data, CLoader)`, because the guard is file-level, not
   name-bound.
2. **Attempt 2 — class-shadow exclusion.** Adding
   `pattern-not-inside: class $LOADER(...)` fixed the isolated case but failed
   in files with multiple classes: semgrep binds sequence patterns at their
   first match, so only the first shadowed call was excluded. The guard had to
   live *inside* the branch (where `$LOADER` binds from the call site) rather
   than as a separate file-level constraint.
3. **Attempt 3 — unification without regex.** Pure unification
   (`from yaml import $LOADER` + `yaml.load(..., $LOADER)`) is name-precise but
   flags **any** from-imported name — including `SafeLoader`. Caught by
   `tn-safe-loader-from-import.py`: `from yaml import SafeLoader;
   yaml.load(data, SafeLoader)` matched. The unsafe-name regex was restored
   alongside unification.
4. **Final.** Unification + regex + shadow exclusion: all five guard files
   silent, all nine gap shapes detected, baseline suite green
   (`reproduction/guard-battery.txt`, `test-suite-differential.txt`).

## 8. Test strategy and results

The upstream test file (`rule/avoid-pyyaml-load.py`) was extended in place,
following repo conventions (`#ruleid:` / `#ok:` annotations):

- **8 new true positives** — one per testable gap shape, including in-function
  from-imports and multi-name import statements.
- **6 new true negatives** — positional `SafeLoader`/`CSafeLoader`/`BaseLoader`
  (module-qualified and from-imported), `yaml.full_load` (codifying the
  maintainers' scope decision), and a local safe class named `Loader` shadowing
  the import.

Results:

- **Improved rule vs extended suite:** 1/1 pass, all annotations satisfied;
  `semgrep validate`: 0 fatal errors.
- **Original rule vs extended suite:** fails with `missing findings lines 70,
  76, 81, 86, 91, 97, 103, 109` — exactly the 8 new true positives. The tests
  are regression-detecting: they fail on the pre-fix rule, so the suite cannot
  silently pass without the fix.

## 9. Measurement: false-positive impact

The question any maintainer asks first: *what does this wake up in real code?*
The battery (`measurement/measure_fp.py`, self-contained) scans six established
Python projects with the original and improved rules and diffs the finding
sets. The original rule is fetched from the pinned baseline SHA, so the table
is reproducible bit-for-bit. An empty `.semgrepignore` is planted before each
scan so semgrep's default ignore list (which skips `tests/` and `examples/`)
cannot silently shrink the corpus — an earlier measurement run without this
step reported false zeros.

| Corpus | Files scanned | Before | After | New findings |
| --- | --- | --- | --- | --- |
| psf/requests | 37 | 0 | 0 | 0 |
| pallets/flask | 83 | 0 | 0 | 0 |
| yaml/pyyaml @ HEAD | 49 | 2 | 2 | 0 |
| docker/compose @ 1.29.2 | 92 | 0 | 0 | 0 |
| saltstack/salt | 3,120 | 0 | 0 | 0 |
| PyCQA/bandit | 196 | 1 | 1 | 0 |
| **Total** | **3,577** | **3** | **3** | **0** |

Interpretation, stated honestly:

- **0 new false positives** and **0 lost findings** across the battery. Salt
  routes all YAML through a `SaltYamlSafeLoader` wrapper (verified by reading
  the hit candidates), bandit's positional-safe canaries
  (`examples/yaml_load.py:25-28`, annotated "no issue should be found") stay
  silent, and pyyaml's two baseline findings are preserved unchanged.
- **0 new true positives at HEAD of these repositories.** The in-scope legacy
  forms are rare in 2026 because the ecosystem migrated to `safe_load` —
  consistent with this rule's `audit` subcategory: it exists to catch the
  residue, not the mainstream. The gap is real in the population this rule
  targets (legacy and audit-grade codebases); the probe corpus demonstrates
  detection, the battery demonstrates restraint.
- **Industry precedent for the call surface:** bandit's B506 example file
  (`examples/yaml_load.py`) deliberately enumerates positional loader forms —
  both unsafe (`Loader=yaml.Loader`) and positional-safe
  (`yaml.load("{}", yaml.SafeLoader)` marked as non-findings) — confirming
  that positional loader resolution is considered in-scope for unsafe-YAML
  detection by another major OSS SAST tool.

## 10. Scope decisions and limitations

Decisions taken *against* expanding the rule, with reasons:

- **`yaml.full_load` / `FullLoader` stays unflagged.** FullLoader is a
  deliberate middle ground; a prior upstream PR (#2352) proposing to flag it
  was closed unmerged, and the baseline rule's confidence model reflects that
  stance. The new TN case codifies it so future contributors don't relitigate
  by accident.
- **Bare `yaml.load(data)` (no loader argument) stays unflagged.** PyYAML ≥ 6.0
  makes the argument mandatory; < 5.1 defaulted it to the unsafe loader, but
  flagging argument-less calls in 2026 would be noise on dead code paths.
- **`from yaml import *` is not resolved.** The engine does not expand
  star-imports; `from yaml import *; load(data, UnsafeLoader)` remains a
  theoretical miss. This is an engine-level limitation, not fixable in rule
  grammar, and matches the baseline rule's (already accepted) exposure for
  `unsafe_load` via star-import.
- **Aliased from-imports** (`from yaml import CLoader as CL; load(data, CL)`)
  are not matched by the bare-name branch — verified empirically
  (`reproduction/probes/edge-alias-from-import-residual.py`): the import
  statement binds the alias `CL`, which neither unifies with the regex-guarded
  loader name nor resolves to it. Residual gap, low prevalence, documented for
  future work.
- **Positional call *before* the class definition** in the same file evades
  the shadow exclusion (pattern ranges extend forward from the class), so the
  call is flagged — verified in
  `reproduction/probes/edge-call-before-shadow.py`. Flagging is semantically
  correct there (at call time the name still resolves to the yaml import);
  documented so reviewers are not surprised by the asymmetry.

## 11. Upstreaming plan

1. File the issue (`upstream/ISSUE.md`) with the minimal reproduction and the
   gap taxonomy — giving maintainers the chance to redirect scope before a PR
   lands.
2. Submit the PR (`upstream/PR_DESCRIPTION.md`) referencing the issue: two
   files changed (`avoid-pyyaml-load.yaml`, `avoid-pyyaml-load.py`), no
   metadata changes, message text updated to mention `unsafe_load_all`.
3. CI expectations: `semgrep-rule-lints` and the `semgrep test --pro .` suite
   must stay green; the extended test file is designed to pass both.
4. Sign the CLA when the bot posts it; respond to review in small, fast
   iterations.
5. If maintainers prefer the positional bare-name branch dropped (strictest
   FP posture), the keyword+`unsafe_load_all`+module-qualified-positional
   subset stands alone — the branches are independent.

## 12. Reproduction appendix

```bash
# environment
pip install semgrep==1.183.0      # CLI used for every number in this study
python3 -c "import yaml; print(yaml.__version__)"   # 6.0.3

# baseline rule (pinned)
curl -sSL -o orig.yaml https://raw.githubusercontent.com/semgrep/semgrep-rules/16b9e6d45f10649f6a531ec4838ed9924372c3bc/python/lang/security/deserialization/avoid-pyyaml-load.yaml

# probe evidence (before: 7 matches / after: 16)
semgrep scan --config orig.yaml   --no-git-ignore --metrics=off reproduction/probes/
semgrep scan --config rule/avoid-pyyaml-load.yaml --no-git-ignore --metrics=off reproduction/probes/

# test-suite differential
SEMGREP_SEND_METRICS=off semgrep test --config orig.yaml rule/avoid-pyyaml-load.py      # FAILS
SEMGREP_SEND_METRICS=off semgrep test --config rule/avoid-pyyaml-load.yaml rule/avoid-pyyaml-load.py  # PASSES

# false-positive battery (first run clones ~120 MB of corpora)
cd measurement && python3 measure_fp.py
```

All timings negligible except the corpus clone; total end-to-end under ten
minutes on a laptop-class machine.
