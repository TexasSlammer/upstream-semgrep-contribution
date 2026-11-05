# Rule variants (alternatives measured, not shipped)

Both files here are complete, valid rule definitions benchmarked in
`measurement/benchmark-variants.txt`. The shipped rule remains
`../avoid-pyyaml-load.yaml` (metavariable formulation, passes the full
upstream test suite including the local-class shadow true-negative).

## `avoid-pyyaml-load-reduced.yaml` — reduced-cost fallback

Baseline rule + `yaml.unsafe_load_all` + bare-name from-import branches;
the two positional module-qualified branches are removed.

- Scan time on salt (3,121 files): 13.5 s (~2.0x original) — measured;
  metavariable-unification branches carry the cost even alone, so this is
  NOT a large saving (documented honestly).
- Coverage: 14/17 probe findings; fails the extended test file only on the
  three positional module-qualified true positives (lines 81, 86, 91).
- Use if: you accept the ~2x cost but not the module-qualified positional
  branches specifically.

## `avoid-pyyaml-load-enumerated.yaml` — fast formulation

Replaces metavariable-regex unification with enumerated literals.

- Scan time on salt: 6.9 s (~1.0x original) — the fastest correct-schema
  formulation we measured.
- Coverage: 19/17 probe findings — additionally DETECTS aliased
  from-imports (`from yaml import CLoader as CL; yaml.load(x, CL)`), a
  shape the shipped rule documents as a residual gap, with a real-world
  demonstration in `reproduction/realworld/`.
- Known tradeoff: the engine resolves identifiers through its import
  table, so a file containing both `from yaml import Loader` and a later
  local `class Loader(yaml.SafeLoader)` rebind produces one finding where
  Python semantics say the call is safe. This fails the shipped test file's
  `local_safe_loader_shadow` true-negative (line 139). The shape did not
  occur in any of the six pinned real-world corpora (3,578 files, 0
  findings delta) — see the FP battery.
- Use if: you prefer baseline speed + wider coverage and accept that one
  synthetic FP class, e.g. with the shadow TN test adjusted accordingly.

Neither variant is a drop-in replacement for the shipped rule's test file;
each documents its own expectation deltas above.
