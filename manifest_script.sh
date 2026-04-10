#!/bin/sh
set -eu

export XBPS_YES=1
echo ">>> Installing container dependencies..."
xbps-install -Syu || true
xbps-install -y bash git curl tar coreutils findutils

echo ">>> Cloning void-packages to utilize native xgensum..."
git clone --depth=1 https://github.com/void-linux/void-packages.git /tmp/void-packages

cd /tmp/void-packages

# THE FIX: Apply your exact bypass configuration from build.yml so xbps-src can run as root safely!
echo "XBPS_CHROOT_CMD=ethereal" >> etc/conf
echo "XBPS_ALLOW_CHROOT_BREAKOUT=yes" >> etc/conf

# Copy our templates over into the build chroot
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
  ./xbps-src xgensum -f -i "$pkg" || true
  
  # Copy the perfectly formatted template back to your repo
  cp srcpkgs/$pkg/template /workspace/$pkg/template
done < /workspace/changed_packages.txt
