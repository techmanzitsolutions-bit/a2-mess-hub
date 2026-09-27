#!/usr/bin/env bash
set -euo pipefail

ROOT=/srv/techmanz/a2-mess
PUBLIC_URL="https://techmanz-server.tailbdad47.ts.net"

sudo tee /usr/local/bin/a2-postboot-verify.sh >/dev/null <<'VERIFY'
#!/usr/bin/env bash
set -u
ROOT=/srv/techmanz/a2-mess
PUBLIC_URL="https://techmanz-server.tailbdad47.ts.net"
OUT="$ROOT/logs/PRODUCTION-BOOT-VERIFY.txt"
mkdir -p "$ROOT/logs"
exec >"$OUT" 2>&1

echo "A2 MESS HUB POST-BOOT VERIFY"
echo "Time: $(date -Is)"
PASS=1

for C in techmanz-postgres a2mess-api a2mess-web-staging; do
  if [[ "$(docker inspect -f '{{.State.Status}}' "$C" 2>/dev/null)" == "running" ]]; then
    echo "PASS: $C running"
  else
    echo "FAIL: $C not running"
    PASS=0
  fi
done

if systemctl is-active --quiet tailscaled; then
  echo "PASS: tailscaled active"
else
  echo "FAIL: tailscaled inactive"
  PASS=0
fi

if tailscale funnel status 2>/dev/null | grep -q 'Funnel on'; then
  echo "PASS: Tailscale Funnel active"
else
  echo "FAIL: Tailscale Funnel inactive"
  PASS=0
fi

if curl -fsS http://127.0.0.1:3200/app.html | grep -q 'TECH MANZ server'; then
  echo "PASS: local frontend"
else
  echo "FAIL: local frontend"
  PASS=0
fi

if curl -fsS http://192.168.1.112:3100/health | grep -q '"status":"ok"'; then
  echo "PASS: local API"
else
  echo "FAIL: local API"
  PASS=0
fi

if curl -fsSL --connect-timeout 10 --max-time 30 "$PUBLIC_URL/app.html" | grep -q 'TECH MANZ server'; then
  echo "PASS: public Funnel frontend"
else
  echo "FAIL: public Funnel frontend"
  PASS=0
fi

if curl -fsSL --connect-timeout 10 --max-time 30 "$PUBLIC_URL/api/health" | grep -q '"status":"ok"'; then
  echo "PASS: public Funnel API"
else
  echo "FAIL: public Funnel API"
  PASS=0
fi

if [[ "$PASS" == "1" ]]; then
  echo "A2 MESS HUB POST-BOOT VERIFY PASSED"
  exit 0
fi

echo "A2 MESS HUB POST-BOOT VERIFY FAILED"
exit 1
VERIFY

sudo chmod 750 /usr/local/bin/a2-postboot-verify.sh

sudo tee /etc/systemd/system/a2-postboot-verify.service >/dev/null <<'UNIT'
[Unit]
Description=A2 MESS HUB post-boot verification
After=network-online.target docker.service tailscaled.service
Wants=network-online.target
Requires=docker.service tailscaled.service

[Service]
Type=oneshot
ExecStartPre=/bin/sleep 30
ExecStart=/usr/local/bin/a2-postboot-verify.sh

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable a2-postboot-verify.service >/dev/null

# Stop the old temporary Cloudflare Quick Tunnel if it is still running.
if [[ -f /tmp/a2mess-quick-tunnel.pid ]]; then
  P="$(cat /tmp/a2mess-quick-tunnel.pid 2>/dev/null || true)"
  if [[ -n "$P" ]] && kill -0 "$P" 2>/dev/null; then
    CMD="$(ps -p "$P" -o args= 2>/dev/null || true)"
    if [[ "$CMD" == *cloudflared* && "$CMD" == *"--url"* ]]; then
      kill "$P" 2>/dev/null || true
    fi
  fi
  rm -f /tmp/a2mess-quick-tunnel.pid
fi

mkdir -p "$ROOT/logs"
cat > "$ROOT/PRODUCTION-FROZEN.txt" <<EOF
A2 MESS HUB - TECH MANZ PRODUCTION FROZEN
Frozen at: $(date -Is)
Public URL: $PUBLIC_URL
LAN URL: http://192.168.1.112:3200
Runtime: TECH MANZ Ubuntu server
Database: PostgreSQL local
Bill/image storage: local
Public ingress: Tailscale Funnel
Normal users require VPN: NO
Firebase runtime dependency: NO
Cloudinary runtime dependency: NO
Uploadcare runtime dependency: NO
GitHub Pages runtime dependency: NO
EOF

echo
echo "============================================================"
echo " FINAL REBOOT CHECK INSTALLED"
echo " Public URL: $PUBLIC_URL"
echo " Boot verifier: enabled"
echo " Production freeze manifest: $ROOT/PRODUCTION-FROZEN.txt"
echo "============================================================"
echo "Now run: sudo reboot"
