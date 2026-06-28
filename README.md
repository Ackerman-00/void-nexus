<div align="center">

<img src="https://voidlinux.org/assets/img/void_bg.png" width="80" />

<h1>void-nexus</h1>

<p>A cryptographically signed, self-updating package repository for Void Linux.</p>

[![Build](https://img.shields.io/github/actions/workflow/status/Ackerman-00/void-nexus/build.yml?style=for-the-badge&label=BUILD&logo=githubactions&logoColor=white)](https://github.com/Ackerman-00/void-nexus/actions)
&nbsp;
[![Updates](https://img.shields.io/github/actions/workflow/status/Ackerman-00/void-nexus/check-updates.yml?style=for-the-badge&label=AUTO-UPDATE&logo=github&logoColor=white)](https://github.com/Ackerman-00/void-nexus/actions)

<p><sup>Packages built on-demand · Signed & indexed automatically · Drop-in native xbps repo</sup></p>

</div>

---

## ⚡ Quick Setup

**① Add the repository**

```bash
echo 'repository=https://github.com/Ackerman-00/void-nexus/releases/download/rolling' \
  | sudo tee /etc/xbps.d/10-nexus.conf
```

**② Trust the signing key**

Pre-download the public key so you're never prompted:

```bash
sudo mkdir -p /var/db/xbps/keys && curl -L \
  https://github.com/Ackerman-00/void-nexus/raw/main/public.pem \
  | sudo tee /var/db/xbps/keys/60:e2:6a:be:49:a8:08:c9:fc:94:ea:d8:7a:14:bc:0d.pub >/dev/null
```

Or just run `sudo xbps-install -S` and press `y` when prompted.

**③ Sync and install**

```bash
sudo xbps-install -S
sudo xbps-install <package-name>
```

---

## 📦 Packages

<div align="center">

<sub>Full package list with versions, descriptions, and changelogs.</sub>

</div>

<br />

| Package | Description | Type |
|---------|-------------|:----:|
| `blender-bin` | 3D creation suite (official binary) | Stable |
| `brave-browser` | Privacy-focused web browser | Stable |
| `brave-origin-bin` | Brave Origin browser binary | Stable |
| `dank-material-shell` | Material Design shell for niri | Stable |
| `dgop` | D言語用パッケージマネージャー | Stable |
| `dsearch` | Desktop search utility | Stable |
| `faugus-launcher` | Game launcher for Linux | Stable |
| `gcc16` | GNU Compiler Collection 16 (parallel install) | Snapshot |
| `helium-browser-bin` | Helium browser binary | Stable |
| `heroic-games-launcher` | Epic/GOG games launcher | Stable |
| `libspng` | Simple PNG library | Stable |
| `niri-git` | Scrollable-tiling Wayland compositor | Git |
| `noctalia-qs` | Quick Settings extension for GNOME | Stable |
| `noctalia-shell` | GNOME Shell theme & extensions | Stable |
| `noctalia-v5` | Lightweight Wayland shell | Git |
| `protonplus` | Proton management tool | Stable |
| `quickshell-git` | Quick script launcher | Git |
| `rootapp` | Discord alternative for gaming communities | Stable |
| `sdbus-cpp` | High-level C++ D-Bus library | Stable |
| `tomlplusplus` | Header-only TOML parser for C++ | Stable |
| `vesktop` | Vencord-bundled Discord client | Stable |
| `xwayland-satellite-git` | Rootless Xwayland for any compositor | Git |
| `zed` | High-performance code editor | Stable |
| `zen-browser` | Privacy-focused Firefox-based browser | Stable |

> `Git` packages track upstream HEAD and rebuild on every new commit.

---

## 🔄 Staying Updated

No extra steps — packages update with your system:

```bash
sudo xbps-install -Su
```

---

## 🛠 Troubleshooting

<details>
<summary><b>Repository not found</b></summary>
<br />
Verify <code>/etc/xbps.d/10-nexus.conf</code> contains exactly:

```
repository=https://github.com/Ackerman-00/void-nexus/releases/download/rolling
```
</details>

<details>
<summary><b>Key import failed or was declined</b></summary>
<br />
Place the public key manually:

```bash
sudo mkdir -p /var/db/xbps/keys
curl -L https://github.com/Ackerman-00/void-nexus/raw/main/public.pem \
  | sudo tee /var/db/xbps/keys/60:e2:6a:be:49:a8:08:c9:fc:94:ea:d8:7a:14:bc:0d.pub >/dev/null
```
</details>

<details>
<summary><b>Package not found</b></summary>
<br />
Only <code>x86_64</code> glibc is currently supported. musl and other architectures are not built.
</details>

---

## 🤝 Contributing

Want a package added, or spotted something broken?

- **[Open an issue](https://github.com/Ackerman-00/void-nexus/issues/new)** — request a new package or report a build failure
- **[Submit a PR](https://github.com/Ackerman-00/void-nexus/pulls)** — add your own template under `srcpkgs/<name>/template`
- **Package updates** are handled automatically by the workflow — no need to bump versions manually

---

<div align="center">

Made with 🖤 by [Ackerman-00](https://github.com/Ackerman-00) &nbsp;·&nbsp; Powered by [Void Linux](https://voidlinux.org)

</div>
