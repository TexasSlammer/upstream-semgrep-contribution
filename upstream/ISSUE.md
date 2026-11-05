## Summary

`python.lang.security.deserialization.avoid-pyyaml-load` misses three
families of unsafe PyYAML deserialization calls that are semantically
identical to the shapes it already flags (CWE-502, RCE via
`!!python/object/new:...` tags):

1. **`yaml.unsafe_load_all(...)`** — public API member (applies `UnsafeLoader`
   per document) that the rule never mentions, unlike its sibling
   `yaml.unsafe_load`.
2. **Positional loader argument** — every `yaml.load` / `yaml.load_all`
   pattern requires the `Loader=` keyword form, but PyYAML's documented
   signature is `load(stream, Loader)`; the positional form is legal and
   equivalent.
3. **Positional bare-name loaders via from-imports** — e.g.
   `from yaml import load, CLoader; load(data, CLoader)`.

## Reproduction

semgrep 1.183.0 (PyPI), rule from `develop` @ `16b9e6d45f10649f6a531ec4838ed9924372c3bc`.

```python
import yaml
yaml.unsafe_load_all(payload)              # no finding
yaml.load(payload, yaml.UnsafeLoader)      # no finding
yaml.load_all(payload, yaml.CLoader)       # no finding

from yaml import load, UnsafeLoader
load(payload, UnsafeLoader)                # no finding
```

Control (correctly flagged today, proving the harness):

```python
import yaml
yaml.unsafe_load(payload)                  # finding ✓
yaml.load(payload, Loader=yaml.UnsafeLoader)  # finding ✓
```

Note that the engine's from-import and alias resolution already covers
`from yaml import unsafe_load; unsafe_load(x)` and
`import yaml as y; y.unsafe_load(x)` — the misses above are purely about the
argument forms and the missing API member, not import-style enumeration.

## Why it matters

All missed shapes hand the same unsafe loaders to the same parser entry
points as the covered shapes. The positional convention is PyYAML's
documented signature, and `unsafe_load_all` is not exotic — it is the
documented stream counterpart of `unsafe_load`. As an `audit`-subcategory
rule, this rule's population is exactly the legacy code where these forms
persist.

## Suggested fix

I have a working extension ready to PR: add `yaml.unsafe_load_all(...)`,
regex-guarded positional branches (`^yaml\.(Loader|UnsafeLoader|CLoader)$`),
and a from-import-unified bare-name branch with a local-class shadow
exclusion. Extended test file included: 8 new true positives + 6 new true
negatives (positional SafeLoader/CSafeLoader/BaseLoader stay silent; local
safe `class Loader` stays silent; `yaml.full_load` stays silent, consistent
with the decision in #2352).

## Measured impact

False-positive battery on 6 established repositories (3,578 files, including
yaml/pyyaml, saltstack/salt, PyCQA/bandit, every corpus pinned to its exact
scanned commit): **0 new false positives, 0 lost findings**, re-verified
2026-11-06 as a three-way comparison including a faster alternative
formulation (same result for all variants).

Performance, measured with per-run target-count validation
(saltstack/salt, 3,121 files): original 6.8 s → improved 14.3 s standalone
(~+2.4 ms/file). A full formulation matrix will ship with the PR; the cost
is intrinsic to the metavariable-unification branches (~2x as a group) and
`unsafe_load_all` is free; a baseline-speed enumerated variant exists with a
documented tradeoff (it breaks the local-class shadow test), so the
performance/coverage choice can be explicit rather than hidden.
Absolute framing: ~7.5 s on a 3,000-file repo for an `audit`-subcategory
rule; this repo's CI runs fixture-file tests and is unaffected.

## Real-world confirmation

The gap is not hypothetical. On pinned `home-assistant/core`
(`72ff09425462a2c39d4e0c89bd1ec100ac28b06c`), `tests/test_config.py:453`
calls `list(yaml.unsafe_load_all(fp))` — the original rule reports 0
findings there, the improved rule reports 1 (pinned commands and output
available on request / in the PR). GitHub's CodeQL independently
models `yaml.unsafe_load_all` as a YAML decoding sink
(`python/ql/test/library-tests/frameworks/yaml/Decoding.py`), and bandit's
B506 example corpus (`examples/yaml_load.py:22-28`) treats the positional
loader convention as in-scope, annotating positional *safe* loaders as
expected non-findings.

Happy to open the PR if the scope sounds right — or to trim the bare-name
branch if you prefer the more conservative subset.
