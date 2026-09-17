<div align="center">

# ■ ARCHIVED — This Repository Is Retired

### Looking for an alternative? ▼

[![View voider-repo on Codeberg](https://img.shields.io/badge/Codeberg-view_voider--repo-blue?style=for-the-badge&logo=codeberg&logoColor=white)](https://codeberg.org/voiders-community/repository)

**→ https://codeberg.org/voiders-community/repository ←**

<p><sup><b>void-nexus is no longer maintained and will receive no further updates.</b> As an actively maintained community alternative, you may want to check out <code>voider-repo</code> by voiders-community on Codeberg. Note: that is an independent project, not affiliated with this repo.</sup></p>

</div>

> [!IMPORTANT]
> ## → This repository is retired
> **void-nexus is no longer being maintained and will receive no further updates.**
>
> If you need an actively maintained alternative, consider:
> ### → [codeberg.org/voiders-community/repository](https://codeberg.org/voiders-community/repository)
>
> Note: that is an independent community project, not a continuation of this repo.

---

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
<summary>Click to expand — 19 packages</summary>

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
| `noctalia` | A sleek, customizable desktop shell crafted for Wayland | Git |
| `noctalia-greeter` | Minimal login greeter for greetd matching the look of Noctalia Shell | Stable |
| `protonplus` | Compatibility tools manager for GNOME (Wine/Proton) | Stable |
| `quickshell-git` | Flexible toolkit for making desktop shells with QtQuick (Git Snapshot) | Git |
| `rootapp` | Discord alternative for gaming communities and large online groups | Stable |
| `sdbus-cpp` | High-level C++ D-Bus library | Stable |
| `vesktop` | Custom Discord desktop client with Vencord preinstalled | Stable |
| `xwayland-satellite-git` | Xwayland outside your Wayland compositor (Git Snapshot) | Git |
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
