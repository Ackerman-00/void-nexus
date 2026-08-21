# AGENTS.md — void-nexus

Work-notes for AI agents and humans maintaining this repo.

## Self-healing sweep architecture (added 2026-08-21)

Three-layer defense-in-depth for package staleness and integrity:

### Layer 1: Deterministic Python sweep (`tools/teardown-sweep.py`)

Pure stdlib Python script that runs AFTER the agent exits. Downloads every
artifact, tears it apart (AppImage extract, .deb control, zip internals, Electron
.asar, `application.ini`, ELF `--version` probe), verifies checksums (sha256,
BLAKE2B+SHA512, SRI), reads internal versions, and compares against upstream.

Key functions:
- `resolve_canonical_repo()`: detects GitHub forks via API `parent.full_name`,
  compares against canonical upstream (not the fork)
- `is_chromium_build_number()`: filters Chromium engine build numbers
  (first component >= 50) from version probes
- `versions_match()`: handles both prefix and suffix version alignment
  (e.g. Chromium `143.1.93.137` vs Brave `1.93.137`)
- `fix_stale_pkg()`: mechanical auto-fix — sed version in ebuild/spec/nix/template
- `--autofix` flag: when STALE is detected, auto-fix and re-verify

Exit code = verdict. Exit 0 = all packages verified. Exit 1 = any
FAIL/MISMATCH/STALE/UNVERIFIED → CI opens an issue.

### Layer 2: Agentic self-healing prompt (opencode-schedule.yml PROMPT)

The coding agent's PROMPT includes a SELF-HEALING SWEEP PROTOCOL section that
instructs the agent on what to do when the sweep fails:

1. Read `teardown-report.md` from the previous run
2. For each STALE: investigate deeper (new deps, EAPI change, eclass rename),
   not just version sed
3. For each FAIL/MISMATCH: re-download, verify checksum, update if re-released
4. Never close a teardown issue without passing sweep + evidence
5. False positive defense: fix the sweep script, never weaken checks

This is the "intelligent fixer" layer — handles cases the deterministic
sweep's mechanical `fix_stale_pkg()` cannot (new dependencies, API changes,
package restructuring).

### Layer 3: CI gate + issue auto-open

The workflow's cleanup job opens an issue when the sweep fails (exit 1).
On the next run, the agent reads the issue and the teardown report, fixes
the problems, and the sweep re-verifies. This closes the loop:
detect → report → fix → verify → close.

### Why this architecture

- **Deterministic + intelligent**: the sweep is pure Python (no LLM needed,
  no hallucination, fast). The agent handles complex cases that require
  reasoning about upstream changes.
- **Self-healing**: genuinely stale packages get auto-fixed by the sweep's
  `--autofix` and/or the agent's investigation. False positives get caught
  and the sweep is improved.
- **Proof-or-Stop**: exit code = verdict. No claims without evidence.
  The sweep output is committed to the repo as a receipt.
- **Defense-in-depth**: even if one layer misses, the next catches it.
  Fork detection, Chromium build-number filtering, and version alignment
  prevent the known false positive classes.
