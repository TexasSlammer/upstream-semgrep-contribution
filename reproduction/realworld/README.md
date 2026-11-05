# Real-world finding: home-assistant/core `yaml.unsafe_load_all`

Independently sourced demonstration that the detection gap closed by this
contribution exists in production code, not only in synthetic probes.

## Target (pinned)

- Repository: `https://github.com/home-assistant/core` (the world's most
  widely deployed open-source home automation platform; config loading is
  security-sensitive by design — YAML config is user-supplied)
- Pinned commit: `72ff09425462a2c39d4e0c89bd1ec100ac28b06c` (HEAD when
  captured 2026-11-06; recorded for reproducibility)
- File: `tests/test_config.py` (1,833 lines)
- Line 453: `list(yaml.unsafe_load_all(fp))`
- Excerpt saved next to this file: `home-assistant_test_config_excerpt.py`

The call loads YAML streams with `unsafe_load_all` — per PyYAML's own
documentation, equivalent to applying `UnsafeLoader` per document, i.e.
full arbitrary-python-object construction from YAML content (CVE-2017-18342
class). This is precisely the API member the original rule never mentions.

## Measured delta on the pinned file

```bash
SHA=72ff09425462a2c39d4e0c89bd1ec100ac28b06c
curl -sSL -o /tmp/ha-test_config.py \
  "https://raw.githubusercontent.com/home-assistant/core/$SHA/tests/test_config.py"

# original rule (16b9e6d): 0 findings — the gap
semgrep scan --config avoid-pyyaml-load.original.yaml \
  --no-git-ignore --metrics=off --json /tmp/ha-test_config.py | jq '.results | length'
# -> 0

# improved rule: 1 finding at line 453
semgrep scan --config rule/avoid-pyyaml-load.yaml \
  --no-git-ignore --metrics=off --json /tmp/ha-test_config.py | jq '.results | length'
# -> 1
```

Verified with semgrep 1.183.0: original rule `[]`, improved rule `[453]`.

## Why this file is a fair example

The call sits in the config-loading test harness — the code whose entire
purpose is to exercise the config loader against fixture files. A reviewer
auditing loader choices (exactly this rule's `audit` use case) wants that
call surfaced; it was invisible to the original rule.

## Independent corroboration that the surface matters

1. **GitHub's CodeQL models `yaml.unsafe_load_all` as a taint sink**:
   `github/codeql`, `python/ql/test/library-tests/frameworks/yaml/Decoding.py`
   — `yaml.unsafe_load_all(payload) # $ decodeInput=payload ... decodeFormat=YAML`.
2. **Bandit's B506 example corpus** (`PyCQA/bandit`,
   `examples/yaml_load.py`, lines 22-28) annotates positional loader calls
   — including positional *safe* loaders as expected non-findings — i.e.
   the industry-standard B506 detection surface covers the positional
   argument convention that the original semgrep rule ignores.

## Scope note

This is a demonstration of a real detection delta on a real, pinned,
professional codebase — not a claim of an exploitable vulnerability in
Home Assistant.
