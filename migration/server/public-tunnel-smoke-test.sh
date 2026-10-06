#!/usr/bin/env bash
set -euo pipefail

ORIGIN="${A2_WEB:-http://192.168.1.112:3200}"
LOG="/tmp/a2mess-quick-tunnel.log"
PID="/tmp/a2mess-quick-tunnel.pid"

fail(){ echo "FAIL: $*" >&2; exit 1; }
ok(){ echo "PASS: $*"; }

echo "============================================================"
echo " A2 MESS HUB - PUBLIC TUNNEL SMOKE TEST"
echo "============================================================"

curl -fsS "$ORIGIN/app.html" >/tmp/a2-public-origin.html || fail "Local A2 web origin unavailable"
grep -q 'TECH MANZ server' /tmp/a2-public-origin.html || fail "TECH MANZ frontend marker missing"
ok "Local TECH MANZ A2 origin healthy"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "Installing cloudflared from the official Cloudflare APT repository..."
  sudo mkdir -p --mode=0755 /usr/share/keyrings
  curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
  echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" | sudo tee /etc/apt/sources.list.d/cloudflared.list >/dev/null
  sudo apt-get update
  sudo apt-get install -y cloudflared
fi
ok "cloudflared installed: $(cloudflared --version | head -1)"

if [[ -f "$PID" ]]; then
  OLD="$(cat "$PID" 2>/dev/null || true)"
  if [[ -n "$OLD" ]] && kill -0 "$OLD" 2>/dev/null; then
    kill "$OLD" 2>/dev/null || true
    sleep 2
  fi
  rm -f "$PID"
fi

rm -f "$LOG"
nohup cloudflared tunnel --no-autoupdate --url "$ORIGIN" >"$LOG" 2>&1 &
echo $! > "$PID"

URL=""
for i in $(seq 1 45); do
  URL="$(grep -Eo 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$LOG" | head -1 || true)"
  [[ -n "$URL" ]] && break
  sleep 1
done

[[ -n "$URL" ]] || {
  cat "$LOG" || true
  fail "Cloudflare Quick Tunnel URL was not created"
}

for i in $(seq 1 30); do
  if curl -fsSL "$URL/app.html" >/tmp/a2-public-test.html 2>/dev/null; then
    if grep -q 'TECH MANZ server' /tmp/a2-public-test.html; then
      break
    fi
  fi
  sleep 2
done

grep -q 'TECH MANZ server' /tmp/a2-public-test.html 2>/dev/null || {
  cat "$LOG" || true
  fail "Public tunnel created but A2 frontend validation failed"
}

ok "A2 MESS HUB reachable publicly through outbound tunnel"

echo
echo "============================================================"
echo " PUBLIC TUNNEL SMOKE TEST PASSED"
echo " Temporary public URL: $URL"
echo " PID: $(cat "$PID")"
echo " Log: $LOG"
echo " NOTE: This trycloudflare.com URL is TEST-ONLY."
echo " No DNS records were changed."
echo " No inbound firewall ports were opened."
echo "============================================================"
