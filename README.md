<div align="center">

<img src="https://voidlinux.org/assets/img/void_bg.png" width="72" />

# void-nexus

**A cryptographically signed, fully automated custom package repository for Void Linux.**

[![Build](https://img.shields.io/github/actions/workflow/status/Ackerman-00/void-nexus/build.yml?style=flat-square&label=build)](https://github.com/Ackerman-00/void-nexus/actions)
[![Updates](https://img.shields.io/github/actions/workflow/status/Ackerman-00/void-nexus/check-updates.yml?style=flat-square&label=auto-update)](https://github.com/Ackerman-00/void-nexus/actions)

</div>

---

## Overview

Packages in this repo are built automatically, signed with a private key, and served via GitHub Pages as a native xbps repository. Once added, packages update alongside your regular system with `xbps-install -Su` — no manual intervention needed.

---

## Setup

### 1. Add the repository

```bash
echo 'repository=https://ackerman-00.github.io/void-nexus/x86_64' \
  | sudo tee /etc/xbps.d/10-nexus.conf
```

### 2. Sync and trust the signing key

```bash
sudo xbps-install -S
```

You will be prompted to import the RSA public key for **`Void Template Build Bot <actions@github.com>`** — type `y` and press Enter.

### 3. Install packages

```bash
sudo xbps-install <package-name>
```

---

## Available Packages

| Package | Description | Type |
|---------|-------------|------|
| `zen-browser` | Privacy-focused Firefox-based browser | Stable |
| `vesktop` | Vencord-bundled Discord client | Stable |
| `rootapp` | Discord alternative for gaming communities | Stable |
| `dank-material-shell` | Material Design shell for niri/Hyprland | Stable |
| `noctalia-qs` | Quickshell fork with extended audio/compositor support | Stable |
| `niri-git` | Scrollable-tiling Wayland compositor | Git (HEAD) |
| `xwayland-satellite-git` | Rootless Xwayland for any Wayland compositor | Git (HEAD) |
| and more... | Browse the repo for the full list | Stable / Git |

> Git packages track the latest upstream commit and update daily.

---

## Updating

```bash
sudo xbps-install -Su
```

---

## Troubleshooting

**Repository not found**
Verify `/etc/xbps.d/10-nexus.conf` contains exactly:
```
repository=https://ackerman-00.github.io/void-nexus/x86_64
```

**Key import failed or was declined**
Manually trust the key by placing the public `.plist` file in `/var/db/xbps/keys/`. The key file is available in the root of this repository.

**Package not found**
Only `x86_64` (glibc) is supported. musl and other architectures are not currently built.

---

<div align="center">
<sub>Maintained by <a href="https://github.com/Ackerman-00">Ackerman-00</a> · Powered by <a href="https://voidlinux.org">Void Linux</a></sub>
</div>
