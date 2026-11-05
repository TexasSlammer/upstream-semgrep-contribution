# PUSH GUIDE: from this repo to a merged upstream PR

Follow in order. Total time after the first two commits: ~10 minutes of
commands plus maintainer latency.

## 0. One-time setup

```bash
# fork on the web UI first (creates YOUR-USER/semgrep-rules):
#   https://github.com/semgrep/semgrep-rules/fork

git clone https://github.com/YOUR-USER/semgrep-rules.git
cd semgrep-rules
git remote add upstream https://github.com/semgrep/semgrep-rules.git
git fetch upstream --quiet
```

## 1. Sync to the exact tested baseline (recommended)

The rule was developed against `16b9e6d45f10649f6a531ec4838ed9924372c3bc`.
If `develop` has moved, either rebase onto latest (and re-run the
verification commands from CASE-STUDY §12) or branch from the pinned commit:

```bash
git checkout -b fix/avoid-pyyaml-load-positional-and-unsafe-load-all 16b9e6d
```

## 2. Copy the two PR artifacts in place

```bash
cp /path/to/upstream-semgrep-contribution/rule/avoid-pyyaml-load.yaml \
   python/lang/security/deserialization/avoid-pyyaml-load.yaml
cp /path/to/upstream-semgrep-contribution/rule/avoid-pyyaml-load.py \
   python/lang/security/deserialization/avoid-pyyaml-load.py

git diff --stat   # expect exactly: 2 files changed
```

## 3. Verify locally (must be green before you push)

```bash
pip install semgrep==1.183.0
cd python/lang/security/deserialization
SEMGREP_SEND_METRICS=off semgrep test --config avoid-pyyaml-load.yaml avoid-pyyaml-load.py
semgrep validate avoid-pyyaml-load.yaml
```

Expected: `1/1: ✓ All tests passed` and `Configuration is valid - 0 fatal errors`.

## 4. Commit and push

```bash
git add python/lang/security/deserialization/avoid-pyyaml-load.{yaml,py}
git commit -m "avoid-pyyaml-load: detect unsafe_load_all and positional Loader arguments

The rule only matched the keyword Loader= form and never covered
yaml.unsafe_load_all. Add regex-guarded positional branches for
yaml.Loader/UnsafeLoader/CLoader and a from-import-unified bare-name
branch with local-class shadow exclusion. Extend tests with 8 true
positives and 6 true negatives (positional safe loaders, full_load,
shadow classes stay silent). Measured on 6 repos / 3,577 files:
0 new false positives, 0 lost findings."
git push -u origin fix/avoid-pyyaml-load-positional-and-unsafe-load-all
```

## 5. File the issue first, then the PR

1. Open the issue: https://github.com/semgrep/semgrep-rules/issues/new
   — paste `upstream/ISSUE.md` (title + body). Get the issue number.
2. Open the PR: https://github.com/semgrep/semgrep-rules/compare/develop...YOUR-USER:fix/avoid-pyyaml-load-positional-and-unsafe-load-all
   — paste `upstream/PR_DESCRIPTION.md`, replacing `<ISSUE-NUMBER>` and
   `<YOUR-USER>`.

## 6. What happens next

- **CLA bot** will comment — sign via the link (required before merge).
- **CI** runs `semgrep-rule-lints` and the test suite. If the metadata lint
  complains, the likely culprits are schema formatting, not content — this
  diff keeps baseline metadata byte-identical except `message:`.
- **Review cadence**: community PRs on this repo get maintainer triage
  within days-to-weeks; false-negative fixes currently in flight (#4128,
  #3868, #4122) show the pattern lands. Respond to comments within a day
  when possible; keep the diff at exactly two files.

## 7. If review requests changes

Common asks and ready answers (full detail in WALKTHROUGH.md Q&A):

- "Use enumerated patterns instead of regex" → mechanical flip, behavior
  identical (regex is fully anchored).
- "Drop the bare-name branches (perf)" → severable; keyword + unsafe_load_all
  + module-qualified positional stand alone.
- "Why not FullLoader?" → #2352 precedent; we added a TN test codifying it.

Push follow-ups to the same branch — the PR updates automatically.

## 8. After merge

```bash
git checkout develop && git pull upstream develop
git branch -d fix/avoid-pyyaml-load-positional-and-unsafe-load-all
```

Then update the portfolio repo: flip `upstream/PR_DESCRIPTION.md` status to
merged, add the PR link to README.md, and note the merge in CASE-STUDY.md §11.
