# paste-ready text for github.com/semgrep/semgrep-rules issue
# (Issues > New issue; no issue template is enforced in this repo as of 2026-11)

TITLE:
False negatives in avoid-pyyaml-load: positional Loader argument and unsafe_load_all are not detected

BODY:

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

Measured impact on 6 established repositories (3,577 files, including
yaml/pyyaml, saltstack/salt, PyCQA/bandit): **0 new false positives, 0 lost
findings**. Bandit's own B506 example file (`examples/yaml_load.py`)
enumerates positional loader forms as in-scope, including positional-safe
non-findings.

Happy to open the PR if the scope sounds right — or to trim the bare-name
branch if you prefer the more conservative subset.
