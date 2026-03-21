***

## 📦 How to Use This Repository

This repository is fully automated and cryptographically signed. You don't need to manually download or index files! You can add it directly to your Void Linux system as a custom repository, which means you get **automatic updates** alongside your regular system packages.

### 🛠️ Step 1: Add the Repository
Run this single command in your terminal. It creates a configuration file that tells your package manager (`xbps`) where to look for our custom packages:

```bash
echo 'repository=https://ackerman-00.github.io/void-template/x86_64' | sudo tee /etc/xbps.d/10-void-template.conf
```

### 🔐 Step 2: Sync and Trust the Key
Update your package manager's index. Because our packages are securely signed, your system will ask you to verify the key the first time you sync.

```bash
sudo xbps-install -S
```
> **⚠️ Important:** You will see a prompt asking if you want to import the RSA public key for `Void Template Build Bot <actions@github.com>`. Type **`y`** and press Enter.

### 🚀 Step 3: Install Packages!
You can now install any of our custom packages using the standard Void Linux commands.

```bash
# Example Installations:
sudo xbps-install zen-browser
sudo xbps-install rootapp
sudo xbps-install quickshell-git
sudo xbps-install vesktop
```

### 🔄 Keeping Things Updated
Because you added this as a native repository, you never have to worry about manually downloading new releases. Whenever I push an update, it will automatically install the next time update your Void Linux system:

```bash
sudo xbps-install -Su
```

***
