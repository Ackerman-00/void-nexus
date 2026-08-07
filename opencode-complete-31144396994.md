# opencode completion report — void-nexus (run 31144396994)

Date: 2026-08-07. Autonomous maintainer (opencode, agent=build).
Relay pickup: previous relay status was complete; nothing unfinished to resume.

## Failed-build triage
- Recent "Build Nexus XBPS" runs: all SUCCESS (incl. 31143637831 helium/zen/noctalia,
  31144741357 noctalia-greeter, 31145186585 noctalia-greeter rev2, 31146256621 msnap).
- One "Check and Update Package Versions" run (31121236826, 2026-08-06 16:50) FAILED;
  logs already expired under Actions retention so no root cause extractable. All later
  check-updates runs succeeded and correctly bumped helium + zen + noctalia. Treated as
  transient; no residual impact.

## Version inventory sweep (100%: 19 srcpkgs + 8 gcc16 subpackages)
Authority: upstream GitHub API (releases/latest + tags), `git ls-remote HEAD`, and
artifact tear-down (rootapp). All checked this run.

| package | packaged | upstream latest | status |
|---|---|---|---|
| blender-bin | 5.2.0 | 5.2.0 | up-to-date |
| brave-browser | 1.93.132 | v1.93.132 | up-to-date |
| brave-origin-bin | 1.93.132 | v1.93.132 (deb+zip 200) | up-to-date |
| faugus-launcher | 2.0.6 | 2.0.6 | up-to-date |
| gcc16 | 16.1.1+20260801 | GCC 16.1 branch snapshot | up-to-date (manual) |
| helium-browser-bin | 0.15.2.1 | 0.15.2.1 | up-to-date |
| heroic-games-launcher | 2.22.0 | v2.22.0 | up-to-date |
| libspng | 0.7.4 | v0.7.4 | up-to-date |
| msnap | 0.6.1 rev3 | 0.6.1 | UPDATED (rev bump, +bash) |
| noctalia-greeter | 1.2.1 rev2 | v1.2.1 | UPDATED (1.1.0 -> 1.2.1, +bash) |
| niri-git | feb3e43 | = HEAD | up-to-date |
| noctalia | 0ad7d80 | = HEAD | up-to-date |
| protonplus | 0.5.22 | v0.5.22 | up-to-date |
| quickshell-git | 28771c7 | = HEAD | up-to-date |
| rootapp | 0.9.126 | 0.9.126 (sq.version + fedora-nexus spec) | up-to-date |
| sdbus-cpp | 2.3.1 | v2.3.1 | up-to-date |
| vesktop | 1.6.5 | v1.6.5 | up-to-date |
| xwayland-satellite-git | 8d135d3 | = HEAD | up-to-date |
| zen-browser | 1.21.11b | 1.21.11b | up-to-date |

Git distfile checksums verified (download + sha256 vs template): niri, quickshell,
noctalia, xwayland-satellite — all match.

## Changes pushed (main directly, no PRs)
1. 9ecae4b — noctalia-greeter 1.1.0 -> 1.2.1 (checksum 1d1c43...587e1).
2. 251c34d (with 036006c) — noctalia-greeter depends +bash, revision 1 -> 2.
   Root cause: upstream publishes only git tags (no releases/latest) so the
   auto-updater never saw 1.2.1; shipped helper scripts are `#!/usr/bin/env bash`.
3. 816861c — msnap depends +bash (bashly-generated `#!/usr/bin/env bash` CLI),
   revision 2 -> 3; refreshed stale satty comment (satty is now packaged in Void).
4. 89b8fe — .opencode-relay.md ledger updated.

NOTE (blocker recorded): an improvement to check-updates.yml (fall back to the highest
semver *tag* when a repo has no releases/latest) was authored and python-syntax-tested,
but could NOT be pushed: this environment's GitHub App/GITHUB_TOKEN lacks `workflows`
write and GitHub rejects pushes updating `/.github/workflows/*` without it. Available
scopes: contents + PRs + issues + actions. Non-blocking now (noctalia-greater bumped
manually); a future run holding a `workflows`-write token should apply it so tags-only
repos stop going stale.

## Release consistency (step 3)
- Built a local xbps repo from rolling binaries (27 packages registered, xman-rindex).
- Compared each template's expected `<pkg>-<ver>_<rev>.x86_64.xbps` vs rolling assets:
  27/27 match (19 srcpkgs + 8 gcc16 subpackages). No missing/stale binaries.

## Dependency deep audit table
| package | upstream deps found | in template | added/dropped | status |
|---|---|---|---|---|
| noctalia-greeter | nlohmann_json (json?), wlroots0.20, stb, tomlplusplus, povish | json-c++, wlroots0.20-devel, MesaLib-devel... | +bash (runtime) | deps-fixed |
| msnap | bashly bash CLI + grim/slurp/wl-clipboard/gpu-screen-recorder/ffmpeg/jq/xdg | bash missing | +bash | deps-fixed |
| niri/noctalia/quickshell/xwayland-satellite | Cargo/CMake deps | matching build+runtime deps | none | deps-verified |
| brave-browser | none required (shlib hooks) | resolved from build | none | deps-verified |
| sdbus-cpp, libspng, faugus, heroic, helium, zen, vesktop | resolved at build+install | none | none | deps-verified |
Confidence: high for re-derived (noctalia-greeter, msnap, 4 git pkgs); medium for
untouched stable pkg (unchanged since last audit, all installed clean).

## Install-test table (fresh ghcr.io/void-linux/void-glibc-full, trusted public.pem)
| package | build | xbps install | smoke | status |
|---|---|---|---|---|
| helium-browser-bin 0.15.2.1 | soft | RC0 | helium --version exit0 | installable |
| zen-browser 1.21.11b | soft | RC0 | zen --version exit0 | installable |
| noctalia 5.0.0+0ad7d80 | soft | RC0 | noctalia --version v5.0.0 exit0 | installable |
| noctalia-greeter 1.2.1_2 | soft | RC0 | print-greetd-config exit0 (was bash missing) | fixed |
| msnap 0.6.1_3 | soft | RC0 | msnap --help exit0 (was bash missing) | fixed |
| niri, quickshell, xwayland-satellite | soft | RC0 | niri --version; xws headless daemon | installable |
| gcc16 + 8 subpkgs | soft | RC0 | gcc16 --version 16.1.1 | installable |
| blender-bin 5.2.0 | soft | RC0 | blender --version 5.2.0 LTS exit0 | installable |
| brave-browser, brave-origin, heroic, faugus, vesktop, sdbus, libspng, proton | soft | RC0 fresh | electron GUI needs X (no-sandbox as root) - install clean | installable |

electron apps (vesktop, zen, brave, heroic) run as root requires --no-sandbox (expected);
install verified. xwayland-satellite has no CLI flags (headless daemon) — install-clean +
resolved shlibs is the valid check for it.

## Pre-completion gate
1. `git status --porcelain` empty — PASS (shown empty).
2. Every touched pkg has a passing fresh install test incl. fresh-checker re-run
   (noctalia-greeter + msnap): PASS.
3. .opencode-relay.md ledger updated; all changed binaries tested: PASS.
4. Dependency audit covers 100% inventory: PASS.
5. Claims backed by command output (SHAs, run IDs, ls-remote, sha256sum, rolling
   assets, docker/xbps): PASS.
6. Gaps named — see below: PASS.
7. THIS marker file committed at root: opencode-complete-3114417994.md — PASS.

## Not verified (named gaps)
- check-updates.yml mirror fix authored but not pushed (lack of `workflows` write).
- gcc16 snapshot date not re-cross-checked against gcc grow everyone snapshot listing
  (treated as manual; GCC 16.1 branch exists).
- Failed check-updates run 31121236826: logs expired; exact root cause unconfirmed.

## Build-triggered this run
- noctalia-greeter: 31144741357 (rev1), 31145186585 (rev2) — SUCCESS.
- msnap: 31146256621 — SUCCESS.
- Release consistent 27/27; working tree clean; no open issues/PRs.