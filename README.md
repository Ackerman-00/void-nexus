<div align="center">

<img src="https://voidlinux.org/assets/img/void_bg.png" width="80" />

<h1>void-nexus</h1>

<p>A cryptographically signed, self-updating package repository for Void Linux.</p>

[![Build](https://img.shields.io/github/actions/workflow/status/Ackerman-00/void-nexus/build.yml?style=for-the-badge&label=BUILD&logo=githubactions&logoColor=white)](https://github.com/Ackerman-00/void-nexus/actions)
&nbsp;
[![Updates](https://img.shields.io/github/actions/workflow/status/Ackerman-00/void-nexus/check-updates.yml?style=for-the-badge&label=AUTO-UPDATE&logo=github&logoColor=white)](https://github.com/Ackerman-00/void-nexus/actions)

<p><sup>Packages built nightly · Signed & indexed automatically · Drop-in native xbps repo</sup></p>

</div>

---

## ⚡ Quick Setup

**① Add the repository**

```bash
echo 'repository=https://github.com/Ackerman-00/void-nexus/releases/download/rolling' \
  | sudo tee /etc/xbps.d/10-nexus.conf
```

**② Sync and trust the signing key**

```bash
sudo xbps-install -S
```

> You'll be asked to import the RSA key for **`Void Nexus Build Bot <actions@github.com>`** — press `y` to continue.

**③ Install anything**

```bash
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
| `zen-browser` | Privacy-focused Firefox-based browser | Stable |
| `vesktop` | Vencord-bundled Discord client | Stable |
| `rootapp` | Discord alternative for gaming communities | Stable |
| `dank-material-shell` | Material Design shell for niri / Hyprland | Stable |
| `noctalia-qs` | Quickshell fork with extended audio support | Stable |
| `niri-git` | Scrollable-tiling Wayland compositor | Git |
| `xwayland-satellite-git` | Rootless Xwayland for any Wayland compositor | Git |

> `Git` packages track upstream HEAD and rebuild on every new commit.

---

## 🔄 Staying Updated

No extra steps — packages update with your system:

```bash
sudo xbps-install -Su
```

---

## 🤝 Contributing

Want a package added, or spotted something broken?

- **[Open an issue](https://github.com/Ackerman-00/void-nexus/issues/new)** — request a new package or report a build failure
- **[Submit a PR](https://github.com/Ackerman-00/void-nexus/pulls)** — add your own template following the existing structure (one directory per package, containing a `template` file)
- **Package updates** are handled automatically by the workflow — no need to bump versions manually

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
Place the public <code>.plist</code> key file manually into <code>/var/db/xbps/keys/</code>. The key is available in the root of this repository.
</details>

<details>
<summary><b>Package not found</b></summary>
<br />
Only <code>x86_64</code> glibc is currently supported. musl and other architectures are not built.
</details>

---

<div align="center">

Made with 🖤 by [Ackerman-00](https://github.com/Ackerman-00) &nbsp;·&nbsp; Powered by [Void Linux](https://voidlinux.org)

</div>
