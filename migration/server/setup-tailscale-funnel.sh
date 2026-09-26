#!/usr/bin/env bash
set -euo pipefail

ROOT=/srv/techmanz/a2-mess
COMPOSE="$ROOT/web/compose.yml"
BACKUP="$ROOT/backups/tailscale-funnel-$(date +%Y%m%d-%H%M%S)"
LAN_URL="http://192.168.1.112:3200"
LOOP_URL="http://127.0.0.1:3200"

fail(){ echo "FAIL: $*" >&2; exit 1; }
ok(){ echo "PASS: $*"; }

echo "============================================================"
echo " A2 MESS HUB - TAILSCALE FUNNEL SETUP"
echo "============================================================"

command -v tailscale >/dev/null 2>&1 || fail "Tailscale CLI is not installed"
tailscale status >/dev/null 2>&1 || fail "Tailscale is not connected"
ok "Tailscale connected: $(tailscale version | head -1)"

curl -fsS "$LAN_URL/app.html" >/tmp/a2-funnel-lan.html || fail "A2 web app is not healthy on LAN"
grep -q 'TECH MANZ server' /tmp/a2-funnel-lan.html || fail "TECH MANZ frontend marker missing"
ok "A2 MESS HUB LAN origin healthy"

mkdir -p "$BACKUP"
cp -a "$COMPOSE" "$BACKUP/compose.yml.before"

python3 - "$COMPOSE" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text()
loop='127.0.0.1:3200:80'
if loop in s:
    print('Loopback mapping already present')
    raise SystemExit(0)
needle='      - "192.168.1.112:3200:80"'
if needle not in s:
    needle="      - '192.168.1.112:3200:80'"
if needle not in s:
    raise SystemExit('Expected LAN web port mapping not found in compose.yml')
s=s.replace(needle, needle+'\n      - "127.0.0.1:3200:80"', 1)
p.write_text(s)
print('Added loopback-only port mapping for Tailscale Funnel')
PY

docker compose -f "$COMPOSE" config >/tmp/a2-funnel-compose.txt
docker compose -f "$COMPOSE" up -d

for i in $(seq 1 20); do
  if curl -fsS "$LOOP_URL/app.html" >/tmp/a2-funnel-loop.html 2>/dev/null; then break; fi
  sleep 1
done
curl -fsS "$LOOP_URL/app.html" >/tmp/a2-funnel-loop.html || fail "Loopback A2 web listener did not start"
grep -q 'TECH MANZ server' /tmp/a2-funnel-loop.html || fail "Loopback frontend marker missing"
ok "A2 web available on 127.0.0.1:3200 for Funnel"

echo
echo "Starting Tailscale Funnel..."
echo "If Tailscale prints an approval URL, open it in your browser and approve Funnel."
echo

set +e
tailscale funnel --bg 3200
RC=$?
set -e
if [[ "$RC" -ne 0 ]]; then
  echo
  echo "Tailscale Funnel needs approval or another prerequisite."
  echo "After approving the URL shown above, rerun:"
  echo "  tailscale funnel --bg 3200"
  exit "$RC"
fi

sleep 3
tailscale funnel status | tee /tmp/a2-funnel-status.txt
URL="$(grep -Eo 'https://[^ /]+\.ts\.net' /tmp/a2-funnel-status.txt | head -1 || true)"
[[ -n "$URL" ]] || fail "Funnel is active but public ts.net URL was not detected"

PUBLIC_OK=0
for i in $(seq 1 30); do
  if curl -fsSL --connect-timeout 10 --max-time 20 "$URL/app.html" >/tmp/a2-funnel-public.html 2>/dev/null; then
    if grep -q 'TECH MANZ server' /tmp/a2-funnel-public.html; then
      PUBLIC_OK=1
      break
    fi
  fi
  sleep 3
done
[[ "$PUBLIC_OK" == "1" ]] || fail "Funnel URL did not serve A2 MESS HUB"

ok "A2 MESS HUB is publicly reachable through Tailscale Funnel"

echo
echo "============================================================"
echo " A2 MESS HUB TAILSCALE FUNNEL PASSED"
echo " Public URL: $URL"
echo " Local origin: $LOOP_URL"
echo " Backup: $BACKUP"
echo " Funnel runs in background and resumes after reboot."
echo " Normal users do NOT need Tailscale or VPN."
echo "============================================================"
