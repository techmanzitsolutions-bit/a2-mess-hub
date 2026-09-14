from pathlib import Path
import re, sys

# Patch the generated live PWA after all other UI patches have run.
# This keeps every visible "Powered by" location consistent, including the
# first cloud-loading screen, login, settings and desktop/sidebar branding.
if sys.argv[1:]:
    paths=[Path(p) for p in sys.argv[1:]]
else:
    root=Path('/tmp/a2-pwa/www')
    if not root.exists():
        root=Path('www')
    paths=[root/'app.html', root/'index.html']

BRAND='''<div class="powered tm-powered" style="margin-top:18px;display:grid;justify-items:center;gap:4px;color:#7f9d91;font-size:9px;letter-spacing:.08em;text-transform:uppercase"><span>Powered by</span><img src="./tm-solutions-logo.png?v=2" alt="TM Solutions" style="width:112px;max-width:82%;height:auto;display:block;filter:drop-shadow(0 0 9px rgba(38,160,255,.34))"></div>'''
SPLASH_BRAND='''<div class="tech tm-powered" style="position:fixed;bottom:20px;left:0;right:0;display:grid;justify-items:center;gap:4px;color:#8ca89d;font-size:9px;letter-spacing:.08em;text-transform:uppercase"><span>Powered by</span><img src="./tm-solutions-logo.png?v=2" alt="TM Solutions" style="width:112px;max-width:48vw;height:auto;display:block;filter:drop-shadow(0 0 9px rgba(38,160,255,.34))"></div>'''

for page in paths:
    if not page.exists():
        raise SystemExit(f'Branding target not found: {page}')
    s=page.read_text()

    # Upgrade any older injected asset reference first.
    s=s.replace('./tm-solutions-logo.webp','./tm-solutions-logo.png?v=2')

    if page.name == 'app.html':
        # Replace every visible paragraph/block using the old TECHMANZ powered-by label.
        s=re.sub(r'<p\b[^>]*>\s*(?:⚡\s*)?(?:POWERED BY\s+)?TECHMANZ\s*</p>', BRAND, s, flags=re.I)
        s=re.sub(r'<p\b[^>]*>\s*(?:⚡\s*)?POWERED BY\s+TECHMANZ\s*</p>', BRAND, s, flags=re.I)
        s=re.sub(r'<div\b[^>]*class=["\'][^"\']*powered[^"\']*["\'][^>]*>\s*(?:⚡\s*)?(?:POWERED BY\s+)?TECHMANZ\s*</div>', BRAND, s, flags=re.I)
        # Text-only contexts such as WhatsApp/status messages cannot carry an image.
        s=s.replace('Powered by TECHMANZ','Powered by TM Solutions')
        s=s.replace('POWERED BY TECHMANZ','POWERED BY TM SOLUTIONS')
        s=s.replace('⚡ TECHMANZ','TM Solutions')
        if 'tm-solutions-logo.png?v=2' not in s or 'Powered by' not in s:
            raise SystemExit('TM Solutions app branding was not applied')
    else:
        # Entry splash screen shown before app.html.
        s=re.sub(r'<div\b[^>]*class=["\']tech["\'][^>]*>.*?</div>', SPLASH_BRAND, s, count=1, flags=re.I|re.S)
        s=s.replace('Powered by TECHMANZ','Powered by TM Solutions')
        s=s.replace('POWERED BY TECHMANZ','POWERED BY TM SOLUTIONS')
        if 'tm-solutions-logo.png?v=2' not in s:
            s=s.replace('</body>', SPLASH_BRAND+'</body>', 1)
        if 'tm-solutions-logo.png?v=2' not in s:
            raise SystemExit('TM Solutions splash branding was not applied')

    page.write_text(s)
    print('Applied TM Solutions PNG powered-by branding to', page)
