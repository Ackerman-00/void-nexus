## 📦 How to Use This Repository

This repository is fully automated and cryptographically signed. You don't need to manually download or index files! You can add it directly to your Void Linux system as a custom repository, which means you get **automatic updates** alongside your regular system packages.

### 🛠️ Step 1: Add the Repository
Run this single command in your terminal. It creates a configuration file that tells your package manager (`xbps`) where to look for our custom packages:

```bash
echo 'repository=[https://ackerman-00.github.io/void-template/x86_64](https://ackerman-00.github.io/void-template/x86_64)' | sudo tee /etc/xbps.d/10-apex-linux.conf
