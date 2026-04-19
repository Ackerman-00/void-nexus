#!/bin/sh
set -eu

export XBPS_YES=1
echo ">>> Installing container dependencies..."
xbps-install -Syu || true
xbps-install -y bash git curl tar coreutils findutils xtools

echo ">>> Cloning void-packages to utilize native xgensum..."
git clone --depth=1 https://github.com/void-linux/void-packages.git /tmp/void-packages

cd /tmp/void-packages

# Apply bypass from build.yml
echo ">>> Injecting Nexus Masterdir Bypass..."
ln -s / masterdir
echo "x86_64" > /.xbps_chroot_init
echo "XBPS_CHROOT_CMD=ethereal" >> etc/conf
echo "XBPS_ALLOW_CHROOT_BREAKOUT=yes" >> etc/conf

# Copy templates over into the build chroot
find /workspace -maxdepth 2 -name "template" | while read -r tmpl; do
  pkg_dir=$(dirname "$tmpl")
  pkg_name=$(basename "$pkg_dir")
  [ "$pkg_name" = ".github" ] && continue
  cp -r "$pkg_dir" srcpkgs/ 2>/dev/null || true
done

echo ">>> Executing native checksum generation..."
while IFS= read -r pkg; do
  [ -z "$pkg" ] && continue
  echo "Generating native hashes for $pkg..."
  xgensum -f -i "$pkg"
  
  # Copy the perfectly formatted template back to the repo
  cp srcpkgs/$pkg/template /workspace/$pkg/template
done < /workspace/changed_packages.txt
