#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${A2_DOMAIN:-a2messhub.app}"
WWW="www.$DOMAIN"
TEST="server-test.$DOMAIN"
ORIGIN="${A2_WEB:-http://192.168.1.112:3200}"
TUNNEL_NAME="${A2_TUNNEL_NAME:-a2messhub-techmanz}"
HOME_CF="$HOME/.cloudflared"
CFG="$HOME_CF/a2messhub.yml"
QUICK_PID="/tmp/a2mess-quick-tunnel.pid"

fail(){ echo "FAIL: $*" >&2; exit 1; }
ok(){ echo "PASS: $*"; }

echo "============================================================"
echo " A2 MESS HUB - PERMANENT CLOUDFLARE TUNNEL"
echo "============================================================"

curl -fsS "$ORIGIN/app.html" >/tmp/a2-origin-final.html || fail "Local A2 origin unavailable"
grep -q 'TECH MANZ server' /tmp/a2-origin-final.html || fail "TECH MANZ frontend marker missing"
ok "Local TECH MANZ A2 origin healthy"

command -v cloudflared >/dev/null 2>&1 || fail "cloudflared is not installed"
mkdir -p "$HOME_CF"
chmod 700 "$HOME_CF"

# The only interactive step. Cloudflare requires account/zone authorization.
if [[ ! -s "$HOME_CF/cert.pem" ]]; then
  echo
  echo "------------------------------------------------------------"
  echo " ONE-TIME CLOUDFLARE AUTHORIZATION REQUIRED"
  echo " A browser URL will appear below."
  echo " Log in to Cloudflare and authorize/select: $DOMAIN"
  echo " Return here after Cloudflare confirms authorization."
  echo "------------------------------------------------------------"
  cloudflared tunnel login
fi
[[ -s "$HOME_CF/cert.pem" ]] || fail "Cloudflare authorization certificate not created"
ok "Cloudflare account authorization present"

get_tunnel_id(){
  cloudflared tunnel list --output json 2>/dev/null | python3 - "$TUNNEL_NAME" <<'PY'
import json,sys
name=sys.argv[1]
try:
    rows=json.load(sys.stdin)
except Exception:
    rows=[]
for r in rows:
    if r.get("name")==name and not r.get("deletedAt"):
        print(r.get("id") or "")
        break
PY
}

TUNNEL_ID="$(get_tunnel_id || true)"
if [[ -z "$TUNNEL_ID" ]]; then
  cloudflared tunnel create "$TUNNEL_NAME"
  TUNNEL_ID="$(get_tunnel_id || true)"
fi
[[ -n "$TUNNEL_ID" ]] || fail "Could not create/find named Cloudflare tunnel"
CRED="$HOME_CF/$TUNNEL_ID.json"
[[ -s "$CRED" ]] || fail "Tunnel credentials file missing: $CRED"
ok "Named tunnel ready: $TUNNEL_NAME ($TUNNEL_ID)"

cat > "$CFG" <<EOF
tunnel: $TUNNEL_ID
credentials-file: $CRED
no-autoupdate: true
ingress:
  - hostname: $DOMAIN
    service: $ORIGIN
  - hostname: $WWW
    service: $ORIGIN
  - hostname: $TEST
    service: $ORIGIN
  - service: http_status:404
EOF
chmod 600 "$CFG"

cloudflared tunnel --config "$CFG" ingress validate
ok "Tunnel ingress configuration valid"

# Stop the temporary Quick Tunnel now that a named tunnel is ready.
if [[ -f "$QUICK_PID" ]]; then
  QPID="$(cat "$QUICK_PID" 2>/dev/null || true)"
  if [[ -n "$QPID" ]] && kill -0 "$QPID" 2>/dev/null; then
    kill "$QPID" 2>/dev/null || true
    sleep 2
  fi
  rm -f "$QUICK_PID"
fi

# Install/reconfigure the persistent systemd service.
if systemctl list-unit-files cloudflared.service >/dev/null 2>&1; then
  sudo systemctl stop cloudflared 2>/dev/null || true
  sudo cloudflared service uninstall >/dev/null 2>&1 || true
fi
sudo cloudflared --config "$CFG" service install
sudo systemctl enable cloudflared >/dev/null
sudo systemctl restart cloudflared

for i in $(seq 1 30); do
  systemctl is-active --quiet cloudflared && break
  sleep 2
done
systemctl is-active --quiet cloudflared || {
  sudo journalctl -u cloudflared --no-pager -n 80 || true
  fail "Persistent cloudflared service did not start"
}
ok "Persistent cloudflared service active"

# Confirm at least one connector is attached before touching the production hostname.
CONNECTED=0
for i in $(seq 1 30); do
  if cloudflared tunnel info "$TUNNEL_ID" 2>/dev/null | grep -Eqi 'CONNECTOR|Connection|ID'; then
    CONNECTED=1
    break
  fi
  sleep 2
done
[[ "$CONNECTED" == "1" ]] || fail "Named tunnel service started but no connector became visible"
ok "Named tunnel connector online"

echo
echo "Creating safe validation hostname first: $TEST"
if ! cloudflared tunnel route dns "$TUNNEL_ID" "$TEST"; then
  echo "If $TEST already exists in Cloudflare DNS, remove/replace that conflicting record and rerun this script."
  fail "Could not create validation DNS route"
fi

TEST_OK=0
for i in $(seq 1 45); do
  if curl -fsSL --connect-timeout 10 --max-time 20 "https://$TEST/app.html" >/tmp/a2-named-test.html 2>/dev/null; then
    if grep -q 'TECH MANZ server' /tmp/a2-named-test.html; then
      TEST_OK=1
      break
    fi
  fi
  sleep 4
done
[[ "$TEST_OK" == "1" ]] || fail "Named tunnel validation hostname did not serve the TECH MANZ app"
ok "Named tunnel validated publicly at https://$TEST"

echo
echo "Routing production hostname: $DOMAIN"
if ! cloudflared tunnel route dns "$TUNNEL_ID" "$DOMAIN"; then
  echo
  echo "A DNS record for $DOMAIN already exists and conflicts with the tunnel."
  echo "No server rollback is required. The named tunnel is healthy at https://$TEST"
  echo "Remove the old $DOMAIN A/AAAA/CNAME record in Cloudflare DNS, then rerun this script."
  fail "Production DNS route not changed because of an existing record"
fi

# www is convenient but not a production blocker.
if ! cloudflared tunnel route dns "$TUNNEL_ID" "$WWW"; then
  echo "WARN: $WWW has an existing DNS record; apex $DOMAIN will still be used."
fi

PROD_OK=0
for i in $(seq 1 60); do
  if curl -fsSL --connect-timeout 10 --max-time 20 "https://$DOMAIN/app.html" >/tmp/a2-prod-domain.html 2>/dev/null; then
    if grep -q 'TECH MANZ server' /tmp/a2-prod-domain.html; then
      PROD_OK=1
      break
    fi
  fi
  sleep 5
done
[[ "$PROD_OK" == "1" ]] || fail "DNS route created but $DOMAIN has not yet served the TECH MANZ app"

ok "Production HTTPS hostname serves TECH MANZ A2 MESS HUB"

sudo systemctl --no-pager --full status cloudflared | sed -n '1,14p' || true

echo
echo "============================================================"
echo " A2 MESS HUB PERMANENT PUBLIC CUTOVER PASSED"
echo " Production URL: https://$DOMAIN"
echo " WWW URL: https://$WWW"
echo " Validation URL: https://$TEST"
echo " Tunnel: $TUNNEL_NAME"
echo " Tunnel ID: $TUNNEL_ID"
echo " Service: cloudflared (enabled at boot)"
echo " No inbound firewall ports opened."
echo " GitHub Pages/Firebase are no longer required by runtime."
echo "============================================================"
