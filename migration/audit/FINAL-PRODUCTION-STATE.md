# A2 MESS HUB — final production state

Final public runtime verified on 2026-09-27.

- Public URL: https://techmanz-server.tailbdad47.ts.net
- Public ingress: Tailscale Funnel
- Normal users need Tailscale/VPN: no
- Application host: TECH MANZ Ubuntu server
- Database: PostgreSQL on TECH MANZ server
- Bill/image storage: local TECH MANZ server storage
- Firebase runtime dependency: removed
- Cloudinary runtime dependency: removed
- Uploadcare runtime dependency: removed
- GitHub Pages runtime dependency: removed
- Production dataset imported and preflight validated
- 47 referenced bill images validated on local server
- Public Funnel smoke test passed
- Existing LAN access remains available at http://192.168.1.112:3200

The GitHub repository is retained only as source/version-control and migration history; it is not required for production runtime.

Final remaining acceptance gate: reboot the Ubuntu server and verify Docker, PostgreSQL, A2 API, A2 web, Tailscale, and Funnel return automatically, followed by one real browser login over mobile data.
