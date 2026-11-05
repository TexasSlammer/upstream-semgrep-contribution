# WALKTHROUGH: every design decision, annotated

This document is the "defend every line" companion to the case study: a
branch-by-branch annotation of the final rule, the full iteration history
(including the two false-positive introductions that were caught and fixed),
and a Q&A bank for maintainer review and technical interviews.

---

## Part 1 — The final rule, branch by branch

Source of truth: `rule/avoid-pyyaml-load.yaml` (86 lines).

### Lines 3–22: metadata (unchanged)

Kept byte-identical to baseline on purpose. PR reviewers should be able to
see that the change is purely additive to detection logic. The only metadata
edit in the whole PR is the `message:` string (line 26), which now mentions
`unsafe_load_all` so the finding text matches the expanded coverage.

### Lines 37–43: context guards (unchanged)

```yaml
pattern-inside: |
  import yaml
  ...
pattern-not-inside: |
  $YAML = ruamel.yaml.YAML(...)
  ...
```

Two subtleties worth knowing cold:

- `pattern-inside: import yaml` is satisfied even in files that only contain
  `from yaml import ...` — the engine treats from-imports as importing the
  module for scoping purposes. Verified in `probes/gap-classes-1.py`, whose
  first section has no plain `import yaml` and still matches.
- The `ruamel.yaml` exclusion (issue #555 history) survives unchanged; none of
  the new branches interact with it because they all match `yaml.`-prefixed
  callees or names bound by `from yaml import`.

### Line 45: `yaml.unsafe_load(...)` (unchanged)

### Lines 46–51: keyword loader forms (unchanged)

The seven baseline branches. Every new capability had to preserve these
exactly — the first regression gate was "baseline suite must stay green."

### Line 52: `yaml.unsafe_load_all(...)` — NEW, deliberately simple

```yaml
- pattern: yaml.unsafe_load_all(...)
```

No loader-argument machinery needed: the function binds `UnsafeLoader`
internally (`unsafe_load_all(stream)`, verified signature on PyYAML 6.0.3).
The engine's from-import resolution extends this single line to cover
`from yaml import unsafe_load_all; unsafe_load_all(x)` for free — verified in
`probes/gap-classes-2.py:9`. Lesson: check what the engine already gives you
before writing pattern branches for import styles.

### Lines 53–62: positional loader, module-qualified — NEW

```yaml
- patterns:
  - pattern: yaml.load(..., $LOADER)
  - metavariable-regex:
      metavariable: $LOADER
      regex: ^yaml\.(Loader|UnsafeLoader|CLoader)$
```

- `yaml.load(..., $LOADER)` requires a final positional argument. A bare
  `yaml.load(stream)` does not match (PyYAML ≥ 6 requires the argument
  anyway) and keyword calls keep matching the baseline branches.
- The regex is anchored on both ends. `^yaml\.` means the argument must be
  literally `yaml.Loader`, `yaml.UnsafeLoader`, or `yaml.CLoader` — so
  `yaml.load(data, yaml.SafeLoader)`, `yaml.CSafeLoader`, `yaml.BaseLoader`
  cannot match. That TN set is codified in the test file
  (`positional_safe_loaders_module_qualified`).
- Why regex instead of three duplicated patterns (the baseline's house
  style)? Two reasons: three patterns × two functions = six near-identical
  branches to review, and the regex form is what makes the bare-name branch
  below symmetric. If maintainers prefer pattern duplication for consistency,
  that is a trivial mechanical change — noted as an open style question in
  the PR text.

### Lines 63–86: positional loader, bare name via from-import — NEW

```yaml
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
```

This is the heart of the contribution. Three guards, each earning its place
by killing a specific false positive found during iteration:

1. **`pattern-inside: from yaml import $LOADER` + metavariable unification.**
   `$LOADER` appears in *both* the import context and the call. Semgrep
   requires one binding that satisfies both: the name passed positionally must
   be a name actually imported from `yaml`. This is what makes
   `from mypackage import Loader; yaml.load(data, Loader)` (hypothetical local
   loader) not match, and what makes `from yaml import safe_load` + local
   `class CLoader` not match (`safe_load` ≠ `CLoader` — unification fails).
   Verified in `probes/tn-safe-from-import-plus-local-class.py`.
2. **The unsafe-name regex.** Unification alone would match
   `from yaml import SafeLoader; yaml.load(data, SafeLoader)` — a pure false
   positive (SafeLoader is the *recommended* loader!). Caught by
   `probes/tn-safe-loader-from-import.py` during iteration; the regex
   restricts to exactly the three unsafe names. Note the regex no longer
   allows the `yaml.` prefix: that case is handled by the module-qualified
   branch, keeping the two branches disjoint.
3. **The class-shadow exclusion.** `pattern-not-inside` over
   `class $LOADER(...)` + trailing `...` excludes calls that appear after a
   same-named class definition in the file. Required because of a binding
   subtlety: in a file containing *multiple* from-imports (e.g.
   `from yaml import load, CLoader` for a true positive elsewhere), the
   import binds `CLoader` file-wide, which would otherwise unify with a local
   safe `class CLoader` defined further down. Verified in
   `probes/edge-cases.py` (EDGE-C) and `probes/tn-local-class-shadow.py`.
   Known asymmetry: a call *preceding* the class definition is still flagged
   (`probes/edge-call-before-shadow.py`) — which is semantically correct,
   since the name still refers to the yaml loader at that point.

The mirror branch at lines 75–86 repeats the same three guards for
`yaml.load_all`.

---

## Part 2 — Iteration log (the honest version)

| # | Attempt | Result | Kill shot |
| --- | --- | --- | --- |
| 0 | Hypothesized 5 gap classes from reading the rule (from-imports, aliases, positional) | 3 of 5 already covered by engine | Probes FN1–FN5 *matched* the baseline rule — from-import callees and `import yaml as y` aliases resolve. Empiricism over folklore. |
| 1 | Probe for `unsafe_load_all` + positional forms | Both confirmed missed (0 matches on probe2 with working positive control) | The real gap. |
| 2 | Regex-only positional branch (`^yaml\.`) | Caught 3 of 4 positional shapes | from-import bare names normalize to bare text (`CLoader`), failing the regex. |
| 3 | `pattern-inside: from yaml import $ANY` guard + bare regex | New FP: local `class CLoader` in a file with any from-import | Adversarial corpus `probe3.py` EDGE-B/C. |
| 4 | + `pattern-not-inside: class $LOADER(...)` | Fixed isolated files, failed multi-class files | Sequence patterns bind at first match only; guard must live in-branch with call-site binding. |
| 5 | Metavariable unification via `from yaml import $LOADER` | Precise on all shadow cases… | …but flagged `from yaml import SafeLoader` + positional `SafeLoader` (pure FP, `t_f.py`). |
| 6 | Final: unification + unsafe-name regex + in-branch shadow exclusion | 9/9 battery PASS, suite green, validate clean | Shipped. |

Methodological constant: every attempt was run against the *entire* probe
corpus (positives AND negatives), never just the case that motivated it. Two
of the four iteration FPs were caught by negative probes rather than
positives — which is exactly the failure mode reviewers ask about.

---

## Part 3 — Q&A bank

### Questions a semgrep-rules maintainer may ask

**Q1. Why regex guards instead of enumerating the three loader names as
separate patterns, consistent with the baseline style?**
Style consistency is a fair ask; the change is mechanical
(`metavariable-regex` → `pattern-either` of three literal patterns per
function). Offered in the PR; happy to flip. Behavior is identical because
the regex is fully anchored with no wildcards.

**Q2. Does `pattern-inside: from yaml import $LOADER` scale? Is it slow?**
Measured, not hand-waved: on the largest corpus (saltstack/salt, 3,120
Python files), the baseline rule scans in 7.3 s and the improved rule in
15.1 s (~2.5 ms → ~4.8 ms per file; absolute cost stays in the seconds even
on a very large repository). The delta comes from the two unification
branches, which add import-context evaluation per call site. If maintainers
consider that material, the positional bare-name branches are severable —
the keyword, `unsafe_load_all`, and module-qualified-positional coverage
stand alone (see also Q6/§11 of the case study).

**Q3. Why does the message/fix-regex only rewrite `unsafe_load`?**
Pre-existing behavior, left untouched. The `fix-regex` rewrites the matched
`unsafe_load` token to `safe_load`; for positional branches the autofix is a
no-op (no `unsafe_load` token in the match), which is acceptable for an audit
rule. Extending autofix to rewrite `Loader=...`/positional arguments is
future work if wanted.

**Q4. Isn't `yaml.load(data, yaml.Loader)` rare in 2026?**
At HEAD of maintained repos — yes, and §9 of the case study says so plainly
(0 new findings across 3,577 files). This rule is `subcategory: audit`; its
population is legacy and audit-grade code, where the positional convention
(`load(stream, Loader)` — the literal documented signature) persists. The
cost of coverage is measured at zero FPs; the benefit class is the same one
that justified the original rule.

**Q5. `unsafe_load_all` — really used anywhere?**
Rare in the wild, but it is a public, documented API member symmetric to the
already-covered `unsafe_load`, discovered by auditing the module surface
rather than by incident. One line, zero FP footprint on the battery.

**Q6. What about `FullLoader` bypasses (CVE-2020-14343)?**
Out of scope by upstream's own precedent: PR #2352 proposing FullLoader
coverage was closed unmerged. Our change adds a true-negative test codifying
that stance so it is a decision, not an accident.

### Questions an interviewer may ask

**Q: Walk me through how you found the gap.**
A: Treated the rule as a spec of covered shapes, enumerated PyYAML's real API
surface (`inspect.signature` on 6.0.3), diffed, and *proved* every diff
element with a minimal probe file on the pinned baseline before believing it.
Three of five initial hypotheses died on contact with the engine — the
from-import/alias coverage folklore was outdated — which is why proof beats
reading.

**Q: The rule had false positives before. How did you avoid adding more?**
A: Adversarial TN corpus built *alongside* every new branch: safe loaders in
identical syntactic positions, local shadow classes, same-named APIs from
unrelated modules, from-imported safe names. Two of my own intermediate
designs produced FPs that the corpus caught (documented in the iteration
log); the shipped design passes all guards.

**Q: Explain metavariable unification in one breath.**
A: A metavariable bound in one pattern must bind to the same value in all
sibling patterns of a combinator — so `from yaml import $LOADER` in
`pattern-inside` and `$LOADER` in the call pattern force the positional
argument to be a name genuinely imported from yaml. It's dataflow-lite in
rule grammar.

**Q: What would you do differently?**
A: Write the negative corpus first. The `$ANY`-guard FP would have been
caught on day one instead of in iteration 3. Also: check the repo's closed
PRs (#2352, #2178) before designing scope — both scoped decisions I made were
already encoded in repo history.

**Q: How do you know the tests actually test the fix?**
A: Ran the *original* rule against the extended suite and required failure:
it fails with exactly the 8 new true-positive lines missing. A suite that
passes both before and after proves nothing; this one is a regression tripwire.

---

## Part 4 — File-by-file intent

| File | Intent |
| --- | --- |
| `rule/avoid-pyyaml-load.yaml` | The PR artifact. Metadata untouched except `message:`. |
| `rule/avoid-pyyaml-load.py` | The PR's test artifact: baseline cases + 8 TP + 6 TN, upstream annotation style. |
| `reproduction/probes/gap-classes-*.py` | The proof the baseline misses the shapes (paired with `evidence-probe-corpus.txt`). |
| `reproduction/probes/tn-*.py`, `edge-*.py` | The adversarial corpus: silence is the assertion. |
| `reproduction/probes/tp-*.py` | Minimal single-form positives kept out of the multi-form files to avoid file-level context interference. |
| `reproduction/*.txt` | Machine-checkable evidence; regenerate via the commands in CASE-STUDY §12. |
| `measurement/measure_fp.py` | Self-contained FP battery; pins the original rule by SHA so numbers are reproducible. |
| `upstream/*` | Paste-ready issue, PR text, and the exact push commands. |
