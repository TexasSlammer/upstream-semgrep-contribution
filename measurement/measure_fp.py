#!/usr/bin/env python3
"""
False-positive / false-negative regression measurement for the
`python.lang.security.deserialization.avoid-pyyaml-load` rule improvement.

Self-contained: on first run it fetches the ORIGINAL rule from the pinned
semgrep-rules commit, shallow-clones the six corpus repositories, then scans
each corpus with the original and the improved rule and prints the delta.

Usage:
    python3 measure_fp.py                 # clone if needed, then measure
    python3 measure_fp.py --skip-clone    # measure with existing corpora/

Requirements: semgrep >= 1.183.0 on PATH (tested with 1.183.0), git, python3.
"""
import argparse
import json
import os
import subprocess
import sys

# Pinned provenance (update together with docs if you re-run on newer states)
RULE_SHA = "16b9e6d45f10649f6a531ec4838ed9924372c3bc"
ORIGINAL_URL = ("https://raw.githubusercontent.com/semgrep/semgrep-rules/"
                f"{RULE_SHA}/python/lang/security/deserialization/avoid-pyyaml-load.yaml")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
IMPROVED = os.path.join(REPO_ROOT, "rule", "avoid-pyyaml-load.yaml")
ORIGINAL = os.path.join(HERE, "avoid-pyyaml-load.original.yaml")
CORPORA = os.path.join(HERE, "corpora")

# (directory, git url, ref or None for default branch)
# PINNED_COMMITS records the exact HEAD commit each default-branch clone was
# scanned at for the results in fp-scan-results.txt (2026-11-06). Fresh runs
# may advance past them; re-record with `git -C corpora/<name> rev-parse HEAD`.
REPOS = [
    ("requests",       "https://github.com/psf/requests.git",        None),
    ("flask",          "https://github.com/pallets/flask.git",       None),
    ("pyyaml",         "https://github.com/yaml/pyyaml.git",         None),
    ("compose-v1",     "https://github.com/docker/compose.git",      "1.29.2"),
    ("salt",           "https://github.com/saltstack/salt.git",      None),
    ("bandit",         "https://github.com/PyCQA/bandit.git",        None),
]
PINNED_COMMITS = {
    "requests":   "3c7baaa05ab4aa49cc819ce3a819d260de19c157",
    "flask":      "49943b5a94413a530761350f04e896f76e8d620e",
    "pyyaml":     "f5e4504a92f169f65350a1047dccb23bc97028be",
    "compose-v1": "5becea4ca9f68875334c92f191a13482bcd6e5cf",
    "salt":       "4840c2beedf97185289ca7bfe0b98582f8119a07",
    "bandit":     "48ef27bd1bbc32f4e585c92310f7a574e87f6b04",
}


def sh(cmd, cwd=None, allow_rc=(0,)):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode not in allow_rc:
        sys.exit(f"command failed ({r.returncode}): {' '.join(cmd)}\n{r.stderr[:500]}")
    return r


def ensure_original_rule():
    if os.path.exists(ORIGINAL):
        return
    sh(["curl", "-sSL", "-o", ORIGINAL, ORIGINAL_URL])
    print(f"fetched original rule @ {RULE_SHA[:12]} -> {os.path.basename(ORIGINAL)}")


def ensure_corpus():
    os.makedirs(CORPORA, exist_ok=True)
    for name, url, ref in REPOS:
        dest = os.path.join(CORPORA, name)
        if os.path.isdir(dest):
            continue
        cmd = ["git", "clone", "--quiet", "--depth", "1", "--single-branch"]
        if ref:
            cmd += ["--branch", ref]
        cmd += [url, dest]
        sh(cmd)
        print(f"cloned {name}")


def report_pins():
    """Print the exact commit each corpus is scanned at (reproducibility)."""
    print("pinned corpus commits:")
    for name, _, _ in REPOS:
        dest = os.path.join(CORPORA, name)
        if os.path.isdir(dest):
            head = subprocess.run(["git", "-C", dest, "rev-parse", "HEAD"],
                                  capture_output=True, text=True).stdout.strip()
            recorded = PINNED_COMMITS.get(name, "n/a")
            match = "" if head == recorded else "  (MOVED since recorded run)"
            print(f"  {name:<12} {head[:12]}  recorded: {recorded[:12]}{match}")


def scan(cfg, cwd):
    # An empty .semgrepignore in the scan working directory disables semgrep's
    # built-in ignore list; without this, tests/ and examples/ are skipped and
    # the counts would be dishonest.
    sgignore = os.path.join(cwd, ".semgrepignore")
    if not os.path.exists(sgignore):
        open(sgignore, "w").write("")
    r = subprocess.run(["semgrep", "scan", "--config", cfg, "--no-git-ignore",
                        "--metrics=off", "--quiet", "--json", "."],
                       capture_output=True, text=True, cwd=cwd)
    if r.returncode not in (0, 1):
        sys.exit(f"semgrep failed rc={r.returncode}: {r.stderr[:400]}")
    d = json.loads(r.stdout)
    hits = {(os.path.normpath(os.path.join(cwd, x["path"])), x["start"]["line"])
            for x in d["results"]}
    nfiles = len(d.get("paths", {}).get("scanned", []))
    return hits, nfiles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-clone", action="store_true")
    args = ap.parse_args()

    ensure_original_rule()
    if not args.skip_clone:
        ensure_corpus()
    report_pins()

    print(f"\n{'repo':<14} {'files':>7} {'before':>7} {'after':>7} {'delta':>6}")
    print("-" * 46)
    tot_b = tot_a = tot_f = 0
    delta_all = []
    for name, _, _ in REPOS:
        repo_dir = os.path.join(CORPORA, name)
        if not os.path.isdir(repo_dir):
            sys.exit(f"missing corpus {repo_dir}; rerun without --skip-clone")
        bset, nfiles = scan(ORIGINAL, repo_dir)
        aset, _ = scan(IMPROVED, repo_dir)
        delta = sorted(aset - bset)
        tot_b += len(bset)
        tot_a += len(aset)
        tot_f += nfiles
        print(f"{name:<14} {nfiles:>7} {len(bset):>7} {len(aset):>7} {len(delta):>6}")
        for p, l in delta:
            code = open(p, encoding="utf-8", errors="replace").read().splitlines()
            delta_all.append({"repo": name, "path": os.path.relpath(p, repo_dir),
                              "line": l, "code": code[l - 1].strip()})
    print("-" * 46)
    print(f"{'TOTAL':<14} {tot_f:>7} {tot_b:>7} {tot_a:>7} {tot_a - tot_b:>6}")

    out = os.path.join(HERE, "delta_findings.json")
    json.dump(delta_all, open(out, "w"), indent=1)
    print(f"\ndelta findings saved -> {out}")


if __name__ == "__main__":
    main()
