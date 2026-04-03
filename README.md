<div align="center">
<img src="https://www.gentoo.org/assets/img/logo/gentoo-signet.svg" width="80" />
<h1>gentoo-nexus</h1>
<p>An autonomous, self-updating Gentoo overlay and binary host for a bleeding-edge Wayland desktop.</p>

[![Forge](https://img.shields.io/github/actions/workflow/status/Ackerman-00/gentoo-nexus/build.yml?style=for-the-badge&label=FORGE&logo=githubactions&logoColor=white)](https://github.com/Ackerman-00/gentoo-nexus/actions)
&nbsp;
[![Binhost](https://img.shields.io/badge/BINHOST-LIVE-059669?style=for-the-badge&logo=linux&logoColor=white)](https://Ackerman-00.github.io/gentoo-nexus/)
&nbsp;
[![Packages](https://img.shields.io/badge/BROWSE_PACKAGES-→-7c3aed?style=for-the-badge)](https://Ackerman-00.github.io/gentoo-nexus/)

<p><sup>Packages built nightly · Pre-compiled binaries · Drop-in Portage overlay</sup></p>
</div>

---

## ⚡ Quick Setup

**① Add the overlay**

```bash
nano /etc/portage/repos.conf/gentoo-nexus.conf
```

```ini
[gentoo-nexus]
location  = /var/db/repos/gentoo-nexus
sync-type = git
sync-uri  = https://github.com/Ackerman-00/gentoo-nexus.git
priority  = 9999
```

```bash
emaint sync -r gentoo-nexus
```

**② Add the binary host**

```bash
nano /etc/portage/binrepos.conf/nexus.conf
```

```ini
[gentoo-nexus-bin]
priority         = 99999
sync-uri         = https://Ackerman-00.github.io/gentoo-nexus/
verify-signature = false
```

**③ Configure make.conf**

```bash
nano /etc/portage/make.conf
```

```bash
FEATURES="getbinpkg"
EMERGE_DEFAULT_OPTS="--getbinpkg --binpkg-respect-use=n --binpkg-changed-deps=n"
```

> Without `--binpkg-respect-use=n`, Portage rejects pre-built packages whose USE set differs from your local profile and falls back to compiling from source.

---

## 📦 Packages

<div align="center">
<a href="https://Ackerman-00.github.io/gentoo-nexus/">
  <img src="https://img.shields.io/badge/🌐_Browse_All_Packages-Ackerman--00.github.io%2Fgentoo--nexus-7c3aed?style=for-the-badge&logoColor=white" alt="Browse Packages" />
</a>
<br />
<sub>Full package list with versions, descriptions, and build status.</sub>
</div>

<br />

| Package | Description | Type |
|---------|-------------|:----:|
| `gui-wm/niri` | Scrollable-tiling Wayland compositor | Git |
| `gui-wm/mangowc` | Lightweight Wayland compositor layer | Stable |
| `gui-apps/dank-material-shell` | Material Design shell for niri | Stable |
| `gui-apps/quickshell` | Scriptable desktop widget engine | Stable |
| `app-misc/matugen` | Material You color token generator | Stable |
| `x11-misc/xwayland-satellite` | Rootless XWayland for any Wayland compositor | Git |
| `gui-apps/dgop` | Fast application launcher | Stable |
| `app-misc/danksearch` | System-wide fuzzy search | Stable |

> `Git` packages track upstream HEAD and rebuild on every new commit.

---

## 🔄 Staying Updated

No extra steps — packages update with your system:

```bash
emerge -uDNaG @world
```

---

## 🤝 Contributing

Want a package added, or spotted something broken?

- **[Open an issue](https://github.com/Ackerman-00/gentoo-nexus/issues/new)** — request a new package or report a build failure
- **[Submit a PR](https://github.com/Ackerman-00/gentoo-nexus/pulls)** — add your own ebuild following the existing category structure
- **Package updates** are handled automatically by the CI workflow — no need to bump versions manually

---

## 🛠 Troubleshooting

<details>
<summary><b>No binary found for a package</b></summary>
<br />
The forge may still be building it, or a version bump occurred before the nightly run. Trigger a manual build:

Go to **[Actions](https://github.com/Ackerman-00/gentoo-nexus/actions) → Nexus Genesis → Run workflow**, enter the package atom (e.g. `gui-wm/niri`) into the input field, then retry after a few minutes.
</details>

<details>
<summary><b>Binary rejected — USE flag mismatch</b></summary>
<br />
Confirm both flags are present in <code>EMERGE_DEFAULT_OPTS</code> inside <code>/etc/portage/make.conf</code>:

```bash
EMERGE_DEFAULT_OPTS="--getbinpkg --binpkg-respect-use=n --binpkg-changed-deps=n"
```
</details>

<details>
<summary><b>verify-signature warning in emerge output</b></summary>
<br />
Expected and harmless. The binary host does not use Portage GPG signing. The connection is encrypted over HTTPS.
</details>

<details>
<summary><b>Sync fails with an auth error</b></summary>
<br />
The repository is public. Auth errors typically mean a skewed system clock. Fix with:

```bash
ntpd -q
# or
chronyc makestep
```
</details>

<details>
<summary><b>Binary host ignored entirely</b></summary>
<br />
Confirm <code>getbinpkg</code> is in <code>FEATURES</code> and that <code>sync-uri</code> in <code>binrepos.conf</code> ends with a trailing <code>/</code>. Without it, Portage cannot construct the package index URL correctly.
</details>

---

<div align="center">
Made with 🖤 by <a href="https://github.com/Ackerman-00">Ackerman-00</a> &nbsp;·&nbsp; Powered by <a href="https://www.gentoo.org">Gentoo Linux</a>
</div>
