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

**② Sync and install**

```bash
sudo xbps-install -S    # press y when prompted to trust the signing key
sudo xbps-install <package-name>
```

---

## 📦 Packages

<details>
<summary>Click to expand — 20 packages</summary>

<br />

| Package | Description | Type |
|---------|-------------|:----:|
| `blender-bin` | 3D graphics creation suite (binary build) | Stable |
| `brave-browser` | Secure, fast and private web browser with ad blocker | Stable |
| `brave-origin-bin` | Minimalist browser from the makers of Brave (binary release) | Stable |
| `faugus-launcher` | Simple and lightweight app for running Windows games using UMU-Launcher | Stable |
| `msnap` | Screenshot and screencast utility for mango | Stable |
| `gcc16` | GNU Compiler Collection 16 (parallel install) | Snapshot |
| `helium-browser-bin` | Private, fast, and honest web browser based on Chromium | Stable |
| `heroic-games-launcher` | Open source launcher for GOG, Epic, and Amazon Games | Stable |
| `libspng` | Simple, modern libpng alternative | Stable |
| `niri-git` | Scrollable-tiling Wayland compositor (Git Snapshot) | Git |
| `noctalia-qs` | Noctalia Quick Settings - GNOME Shell quick settings extension | Stable |
| `noctalia-shell` | Noctalia Shell - GNOME Shell theme and extensions | Stable |
| `noctalia-v5` | Lightweight Wayland shell built directly on Wayland and OpenGL ES | Git |
| `protonplus` | Compatibility tools manager for GNOME (Wine/Proton) | Stable |
| `rootapp` | Discord alternative for gaming communities and large online groups | Stable |
| `sdbus-cpp` | High-level C++ D-Bus library | Stable |
| `vesktop` | Custom Discord desktop client with Vencord preinstalled | Stable |
| `xwayland-satellite-git` | Xwayland outside your Wayland compositor (Git Snapshot) | Git |
| `zed` | High-performance, multiplayer code editor from the creators of Atom | Stable |
| `zen-browser` | Welcome to a calmer internet | Stable |

> `Git` packages track upstream HEAD and rebuild on every new commit.

</details>

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
sudo mkdir -p /var/db/xbps/keys && sudo curl -L \
  -o /var/db/xbps/keys/b9:f2:38:0f:3f:a7:76:be:5f:ad:01:b9:ef:b5:55:77.plist \
  https://github.com/Ackerman-00/void-nexus/raw/main/signing-key.plist
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
