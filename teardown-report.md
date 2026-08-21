# Teardown Sweep Report

Repo type: **void**. Sweep of **19** packages. Exit code is the verdict; this report is the receipt.
| Package | Distfile | Pinned | Internal | Status | Note |
|---|---|---|---|---|---|
| blender-bin | blender-5.2.0-linux-x64.tar.xz | 5.2.0 | 5.2.0 | **OK** | tar runtime probe blender --version: Blender 5.2.0 LTS
	build date: 2026-07-14
	build time: 01:32:04
	build commit date: 2026-07-13
	build commit time: 15:20 \| hash hash-OK \| pinned 5.2.0 \| internal 5.2.0 |
| brave-browser | brave-browser_1.93.137_amd64.deb | 1.93.137 | 1.93.137 | **OK** | deb pkg=brave-browser (control control.tar.xz) \| hash hash-OK \| pinned 1.93.137 \| internal 1.93.137 |
| brave-origin-bin | brave-origin-1.93.137-linux-amd64.zip | 1.93.137 | 151.1.93.137 | **OK** | zip runtime probe brave --version: Brave Origin 151.1.93.137 unknown \| hash hash-OK \| pinned 1.93.137 \| internal 151.1.93.137 |
| faugus-launcher | 2.1.0.tar.gz | 2.1.0 |  | **SOURCE-OK** | tar extracted, no version evidence found \| hash hash-OK \| source tarball (version = PV by construction) |
| gcc16 | gcc-16.2.0.tar.xz | 16.2.0 | 0.1.0 | **SOURCE-OK** | tar Cargo.toml=0.1.0 (gcc-16.2.0/libgrust/libformat_parser/Cargo.toml) \| hash hash-OK \| weak internal evidence 0.1.0 (not authoritative) |
| gcc16 | gmp-6.3.0.tar.xz | 16.2.0 | 6.2. | **SOURCE-OK** | tar changelog=6.2. (gmp-6.3.0/NEWS) \| hash hash-OK \| weak internal evidence 6.2. (not authoritative) |
| gcc16 | mpfr-4.2.2.tar.xz | 16.2.0 | 4.2.2 | **SOURCE-OK** | tar version file=4.2.2 (mpfr-4.2.2/VERSION) \| hash hash-OK \| weak internal evidence 4.2.2 (not authoritative) |
| gcc16 | mpc-1.3.1.tar.gz | 16.2.0 | 1.3.1 | **SOURCE-OK** | tar changelog=1.3.1 (mpc-1.3.1/NEWS) \| hash hash-OK \| weak internal evidence 1.3.1 (not authoritative) |
| gcc16 | isl-0.27.tar.bz2 | 16.2.0 | 0.27 | **SOURCE-OK** | tar changelog=0.27 (isl-0.27/ChangeLog) \| hash hash-OK \| weak internal evidence 0.27 (not authoritative) |
| gcc16 | gcc-16.1.0-patches-3.tar.xz | 16.2.0 |  | **SOURCE-OK** | tar extracted, no version evidence found \| hash hash-OK \| source tarball (version = PV by construction) |
| helium-browser-bin | helium-0.15.6.1-x86_64_linux.tar.xz | 0.15.6.1 | 0.15.6.1 | **OK** | tar runtime probe chrome --version: Helium 0.15.6.1 (Chromium 151.0.7922.169) \| hash hash-OK \| pinned 0.15.6.1 \| internal 0.15.6.1 |
| heroic-games-launcher | Heroic-2.22.1-linux-x64.tar.xz | 2.22.1 | 2.22.1 | **OK** | tar asar=2.22.1 (Heroic-2.22.1-linux-x64/resources/app.asar) \| hash hash-OK \| pinned 2.22.1 \| internal 2.22.1 |
| libspng | v0.7.4.tar.gz | 0.7.4 |  | **SOURCE-OK** | tar extracted, no version evidence found \| hash hash-OK \| source tarball (version = PV by construction) |
| msnap | v0.6.1.tar.gz | 0.6.1 | 0.6.1 | **SOURCE-OK** | tar version file=0.6.1 (msnap-0.6.1/VERSION) \| hash hash-OK \| weak internal evidence 0.6.1 (not authoritative) |
| niri-git | live niri-wm/niri | b0eb8ad8c800 | b0eb8ad8c800 | **OK** | live niri-wm/niri pin b0eb8ad8c800 vs upstream b0eb8ad8c800 |
| noctalia | live noctalia-dev/noctalia | a064c063f204 | a064c063f204 | **OK** | live noctalia-dev/noctalia pin a064c063f204 vs upstream a064c063f204 |
| noctalia-greeter | v1.2.1.tar.gz | 1.2.1 |  | **SOURCE-OK** | tar extracted, no version evidence found \| hash hash-OK \| source tarball (version = PV by construction) |
| protonplus | v0.6.4.tar.gz | 0.6.4 |  | **SOURCE-OK** | tar extracted, no version evidence found \| hash hash-OK \| source tarball (version = PV by construction) |
| quickshell-git | live https://git.outfoxxed.me/quickshell/quickshell | 9f807554e106 | 9f807554e106 | **OK** | live https://git.outfoxxed.me/quickshell/quickshell pin 9f807554e106 vs upstream 9f807554e106 |
| rootapp | Root-0.9.127-x86_64.AppImage | 0.9.127 | 0.9.127 | **OK** | AppImage 0.9.127 (Root.desktop) \| hash hash-OK \| pinned 0.9.127 \| internal 0.9.127 |
| sdbus-cpp | - | 2.3.1 |  | **OK** | metapackage, no sources to verify |
| vesktop | vesktop_1.6.7_amd64.deb | 1.6.7 | 1.6.7 | **OK** | deb pkg=vesktop (control control.tar.xz) \| hash hash-OK \| pinned 1.6.7 \| internal 1.6.7 |
| xwayland-satellite-git | live Supreeeme/xwayland-satellite | 3bc915f09dd6 | 3bc915f09dd6 | **OK** | live Supreeeme/xwayland-satellite pin 3bc915f09dd6 vs upstream 3bc915f09dd6 |
| zen-browser | zen.linux-x86_64.tar.xz | 1.21.15b | 1.21.15b | **OK** | tar application.ini=1.21.15b (zen/application.ini) \| hash hash-OK \| pinned 1.21.15b \| internal 1.21.15b |
| zen-browser | LICENSE | 1.21.15b |  | **OK** | hash hash-OK \| license/doc file, not an artifact |

**Verdict: PASS** (0 failure(s))
