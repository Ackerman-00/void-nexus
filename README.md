---

# 📦 Void Template Repository

This repository is fully automated and **cryptographically signed**.  
You don’t need to manually download, index, or track updates — just add it to your Void Linux system as a native repository, and packages will update **automatically** along with your regular system updates.

---

## 🚀 Quick Setup

### 1️⃣ Add the repository

Run this single command to create a configuration file that tells `xbps` where to find our custom packages:

```bash
echo 'repository=https://ackerman-00.github.io/void-template/x86_64' | sudo tee /etc/xbps.d/10-void-template.conf
```

### 2️⃣ Sync and trust the key

Update the package index. Because packages are signed, you'll be asked to verify the repository key:

```bash
sudo xbps-install -S
```

> **🔑 Important:**  
> You will see a prompt asking if you want to import the RSA public key for  
> **`Void Template Build Bot <actions@github.com>`**.  
> Type **`y`** and press **Enter** to continue.

### 3️⃣ Install packages

Now you can install any of the available custom packages using standard Void commands:

```bash
# Examples
sudo xbps-install zen-browser
sudo xbps-install rootapp
sudo xbps-install quickshell-git
sudo xbps-install vesktop
```

---

## 🔄 Keeping everything updated

Because this is a native repository, updates are handled automatically. Whenever a new version of a package is built, it will be available the next time you update your system:

```bash
sudo xbps-install -Su
```

---

## 📚 Available Packages

| Package | Description |
|---------|-------------|
| `zen-browser` | A privacy‑focused browser |
| `rootapp` | Some root application |
| `quickshell-git` | A shell utility |
| `vesktop` | A desktop environment component |
| ... and more! | Check the repository for the full list |

> **Note:** The list above is illustrative — see the repository contents for the actual available packages.

---

## ❓ Troubleshooting

- **“Repository not found”** – Make sure the URL in `/etc/xbps.d/10-void-template.conf` is exactly:  
  `https://ackerman-00.github.io/void-template/x86_64`

- **Key import fails** – If you accidentally declined the key, you can manually add it by placing the public key file in `/var/db/xbps/keys/` (the key is named `ackerman-00-void-template.plist` and is available in the repository root).

- **Package not found** – Not all packages are built for every architecture. Currently only `x86_64` (glibc) is supported.

---

Enjoy the automated Void experience! 🚀
