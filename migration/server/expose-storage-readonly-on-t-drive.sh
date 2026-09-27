#!/usr/bin/env bash
set -euo pipefail

SRC=/srv/techmanz/a2-mess/storage
DST=/srv/techmanz/storage/A2-MESS-STORAGE
SMB_USER=techmanz
FSTAB=/etc/fstab
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP=/srv/techmanz/a2-mess/backups/t-drive-storage-view-$STAMP

fail(){ echo "FAIL: $*" >&2; exit 1; }
ok(){ echo "PASS: $*"; }

echo "============================================================"
echo " A2 MESS HUB - READ-ONLY T: DRIVE STORAGE VIEW"
echo "============================================================"

[[ -d "$SRC" ]] || fail "A2 storage source not found: $SRC"
[[ -d /srv/techmanz/storage ]] || fail "Existing T: share root not found: /srv/techmanz/storage"

mkdir -p "$BACKUP"
sudo cp -a "$FSTAB" "$BACKUP/fstab.before"
ok "Backup created: $BACKUP"

if ! command -v setfacl >/dev/null 2>&1; then
  echo "Installing ACL support..."
  sudo apt-get update
  sudo apt-get install -y acl
fi

# Allow the Samba login user to read/traverse A2 storage without giving it write
# access. Existing files get read access; directories get read/traverse access.
sudo find "$SRC" -type d -exec setfacl -m "u:$SMB_USER:rx" {} +
sudo find "$SRC" -type f -exec setfacl -m "u:$SMB_USER:r" {} +

# Make future files/directories created by the API inherit read-only visibility
# for the Samba login user.
sudo find "$SRC" -type d -exec setfacl -m "d:u:$SMB_USER:rx" {} +
ok "Read-only ACL visibility granted to $SMB_USER"

sudo mkdir -p "$DST"

# Remove a stale bind mount if one exists, then mount the live A2 storage at the
# T: share path as read-only. The original path remains writable by the API.
if mountpoint -q "$DST"; then
  sudo umount "$DST"
fi
sudo mount --bind "$SRC" "$DST"
sudo mount -o remount,bind,ro "$DST"
ok "Live read-only bind mount created"

LINE="$SRC $DST none bind,ro,nofail 0 0"
if ! grep -Fqx "$LINE" "$FSTAB"; then
  echo "$LINE" | sudo tee -a "$FSTAB" >/dev/null
fi
ok "Read-only view configured to return after reboot"

# Validate read-only behavior from the normal Samba user context.
if touch "$DST/.a2-write-test" 2>/dev/null; then
  rm -f "$DST/.a2-write-test" || true
  fail "T: storage view is writable; expected read-only"
fi
ok "Write protection confirmed"

FIRST_BILL="$(find "$DST/bills" -maxdepth 1 -type f 2>/dev/null | head -1 || true)"
if [[ -n "$FIRST_BILL" ]]; then
  [[ -r "$FIRST_BILL" ]] || fail "Bill files are not readable from the T: view"
  ok "Bill files readable from T: view"
else
  echo "WARN: No bill file found for read test"
fi

echo
echo "============================================================"
echo " A2 MESS STORAGE VIEW READY"
echo " Windows path: T:\\A2-MESS-STORAGE"
echo " Source: $SRC"
echo " Mode: LIVE + READ-ONLY"
echo " Original API storage remains writable."
echo "============================================================"
