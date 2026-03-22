<div align="center">

<img src="https://voidlinux.org/assets/img/void_bg.png" width="80" />

<br />

# void-nexus

### A cryptographically signed, self-updating package repository for Void Linux.

<br />

[![Build](https://img.shields.io/github/actions/workflow/status/Ackerman-00/void-nexus/build.yml?style=for-the-badge&label=BUILD&logo=githubactions&logoColor=white)](https://github.com/Ackerman-00/void-nexus/actions)
&nbsp;
[![Updates](https://img.shields.io/github/actions/workflow/status/Ackerman-00/void-nexus/check-updates.yml?style=for-the-badge&label=AUTO-UPDATE&logo=github&logoColor=white)](https://github.com/Ackerman-00/void-nexus/actions)
&nbsp;
[![Website](https://img.shields.io/badge/BROWSE_PACKAGES-%E2%86%92-478061?style=for-the-badge)](https://ackerman-00.github.io/void-nexus/)

<br />

> Packages built nightly · Signed & indexed automatically · Drop-in native xbps repo

</div>

---

<br />

## ⚡ Quick Setup

**Three commands and you're done.**

<br />

**① Add the repository**

```bash
echo 'repository=https://ackerman-00.github.io/void-nexus/x86_64' \
  | sudo tee /etc/xbps.d/10-nexus.conf
```

**② Sync and trust the signing key**

```bash
sudo xbps-install -S
```

> You'll be asked to import the RSA key for **`Void Template Build Bot <actions@github.com>`** — press `y` to continue.

**③ Install anything**

```bash
sudo xbps-install <package-name>
```

<br />

---

<br />

## 📦 Packages

<div align="center">

<a href="https://ackerman-00.github.io/void-nexus/">
  <img src="https://img.shields.io/badge/🌐_View_All_Packages-ackerman--00.github.io%2Fvoid--nexus-478061?style=for-the-badge&logoColor=white" alt="Browse Packages" />
</a>

<br /><br />
<sup>Full package list with versions, descriptions, and changelogs.</sup>

</div>

<br />

A few highlights:

| Package | Description | Type |
|---------|-------------|:----:|
| `zen-browser` | Privacy-focused Firefox-based browser | Stable |
| `vesktop` | Vencord-bundled Discord client | Stable |
| `rootapp` | Discord alternative for gaming communities | Stable |
| `dank-material-shell` | Material Design shell for niri / Hyprland | Stable |
| `noctalia-qs` | Quickshell fork with extended audio support | Stable |
| `niri-git` | Scrollable-tiling Wayland compositor | Git |
| `xwayland-satellite-git` | Rootless Xwayland for any Wayland compositor | Git |

> `Git` packages track upstream HEAD and rebuild on every new commit.

<br />

---

<br />

## 🔄 Staying Updated

No extra steps — packages update with your system:

```bash
sudo xbps-install -Su
```

<br />

---

<br />

## 🛠 Troubleshooting

<details>
<summary><b>Repository not found</b></summary>
<br />
Verify <code>/etc/xbps.d/10-nexus.conf</code> contains exactly:

```
repository=https://ackerman-00.github.io/void-nexus/x86_64
```
</details>

<details>
<summary><b>Key import failed or was declined</b></summary>
<br />
Place the public <code>.plist</code> key file manually into <code>/var/db/xbps/keys/</code>. The key is available in the root of this repository.
</details>

<details>
<summary><b>Package not found</b></summary>
<br />
Only <code>x86_64</code> glibc is currently supported. musl and other architectures are not built.
</details>

<br />

---

<br />

<div align="center">

Made with 🖤 by [Ackerman-00](https://github.com/Ackerman-00) &nbsp;·&nbsp; Powered by [Void Linux](https://voidlinux.org)

</div>
