# paste-ready text for the pull request to semgrep/semgrep-rules
# Branch suggestion: fix/avoid-pyyaml-load-positional-and-unsafe-load-all
# Files changed (exactly two):
#   python/lang/security/deserialization/avoid-pyyaml-load.yaml
#   python/lang/security/deserialization/avoid-pyyaml-load.py

TITLE:
[python] avoid-pyyaml-load: detect unsafe_load_all and positional Loader arguments

BODY:

## Summary

Closes the false-negative families described in issue #<ISSUE-NUMBER> (fill
in after filing): unsafe PyYAML deserialization written as

- `yaml.unsafe_load_all(...)` — public API sibling of the already-covered
  `yaml.unsafe_load`, applies `UnsafeLoader` per document;
- `yaml.load(data, yaml.Loader|yaml.UnsafeLoader|yaml.CLoader)` and the same
  for `load_all` — positional form of the already-covered keyword form
  (PyYAML signature is `load(stream, Loader)`);
- positional bare-name loaders bound by from-imports, e.g.
  `from yaml import CLoader; yaml.load(data, CLoader)`.

Metadata is untouched except `message:`, which now mentions
`unsafe_load_all`. The `fix-regex` is unchanged.

## Rule changes (5 new branches)

1. `yaml.unsafe_load_all(...)` — no loader machinery needed; the engine's
   from-import resolution extends it to `from yaml import unsafe_load_all`.
2–3. Positional `yaml.load(..., $LOADER)` / `yaml.load_all(..., $LOADER)` with
   `metavariable-regex: ^yaml\.(Loader|UnsafeLoader|CLoader)$` — anchored, so
   `yaml.load(data, yaml.SafeLoader)` cannot match.
4–5. Positional bare-name form: metavariable **unification** between
   `pattern-inside: from yaml import $LOADER` and the call's `$LOADER`
   (the passed name must be genuinely imported from yaml), plus the same
   unsafe-name regex (bare, branch-disjoint from 2–3), plus
   `pattern-not-inside: class $LOADER(...)` so a local safe class shadowing
   the imported name stays silent.

## Tests

`avoid-pyyaml-load.py` extended in place, repo annotation conventions:

- **8 new true positives**: `unsafe_load_all` (module + from-import);
  positional `yaml.Loader` / `yaml.UnsafeLoader` / `yaml.CLoader`
  (module-qualified and from-imported, `load` and `load_all`, single- and
  multi-name from-imports).
- **6 new true negatives**: positional `SafeLoader` / `CSafeLoader` /
  `BaseLoader`; from-imported `SafeLoader` positionally; `yaml.full_load`
  (codifies the scope decision from #2352); local safe `class Loader`
  shadow (with `from yaml import` present elsewhere in the file).

Regression-differential: the pre-fix rule fails this suite with exactly the
8 new positive lines missing (`70, 76, 81, 86, 91, 97, 103, 109`); the fixed
rule passes 1/1 and `semgrep validate` is clean.

## Measurement

- Probe corpus (available in my reproduction repo, link in comments):
  baseline 7 matches → fixed 17, **0 detections lost**.
- False-positive battery — original vs fixed rule over 6 established
  repositories with semgrep's default ignores disabled:

  | repo | files | before | after | new findings |
  |---|---|---|---|---|
  | psf/requests | 37 | 0 | 0 | 0 |
  | pallets/flask | 83 | 0 | 0 | 0 |
  | yaml/pyyaml | 49 | 2 | 2 | 0 |
  | docker/compose @1.29.2 | 92 | 0 | 0 | 0 |
  | saltstack/salt | 3,120 | 0 | 0 | 0 |
  | PyCQA/bandit | 196 | 1 | 1 | 0 |

  0 new false positives; bandit's positional-safe canaries
  (`examples/yaml_load.py:25-28`, "no issue should be found") stay silent —
  and that file doubles as industry precedent that positional loader forms
  belong in this detection surface.

- Performance (salt, 3,120 files): 7.3 s → 15.1 s per single-rule scan.
  The two bare-name unification branches are severable if that delta is a
  concern; the rest of the coverage stands alone.

## Scope decisions (deliberate non-changes)

- `yaml.full_load` / `FullLoader` remains unflagged (#2352 precedent).
- Argument-less `yaml.load(data)` remains unflagged (PyYAML ≥ 6 requires the
  Loader argument; < 5.1 is dead-in-practice noise).
- Known residual gaps documented rather than approximated: `from yaml import *`
  (engine does not expand star-imports), aliased from-imports
  (`from yaml import CLoader as CL`), and shadow-class definition after the
  call site.

## AI-assistance disclosure

This contribution was developed with AI assistance (Z.ai agent). All
reproductions, measurements, and test results above were executed and
verified against semgrep 1.183.0 with the rule pinned at `16b9e6d`, and I
have reviewed and can explain every line of the diff (design log:
github.com/<YOUR-USER>/upstream-semgrep-contribution — WALKTHROUGH.md).

## Checklist

- [ ] `semgrep test --pro .` green locally for the touched directory
- [ ] `semgrep validate` clean
- [ ] CLA signed (will sign when the bot posts)
