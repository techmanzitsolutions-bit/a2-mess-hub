from pathlib import Path
import re, sys

# Final branding cleanup. Runs after every other UI patch so no legacy branding
# or broken external logo asset can survive anywhere in the generated PWA.
if sys.argv[1:]:
    paths=[Path(p) for p in sys.argv[1:]]
    root=paths[0].parent
else:
    root=Path('/tmp/a2-pwa/www')
    if not root.exists():
        root=Path('www')
    paths=[root/'app.html', root/'index.html']

TM_SVG='''<svg class="tm-logo-svg" viewBox="0 0 220 74" role="img" aria-label="TM Solutions" xmlns="http://www.w3.org/2000/svg">
  <g style="filter:drop-shadow(0 0 5px rgba(54,170,255,.55))">
    <text x="46" y="45" text-anchor="middle" font-family="Arial Black,Arial,sans-serif" font-size="48" font-weight="900" font-style="italic" fill="#39a9ff">T</text>
    <path d="M73 48 L96 12 L91 34 L112 22 L88 58 L94 37 Z" fill="#ffb13b" style="filter:drop-shadow(0 0 5px rgba(255,163,52,.55))"/>
    <text x="147" y="45" text-anchor="middle" font-family="Arial Black,Arial,sans-serif" font-size="48" font-weight="900" font-style="italic" fill="#ff8b31">M</text>
  </g>
  <text x="110" y="69" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="13" font-weight="700" letter-spacing="5" fill="#d9e9e2">SOLUTIONS</text>
</svg>'''

BRAND=f'''<div class="powered tm-powered"><span class="tm-powered-label">Powered by</span>{TM_SVG}</div>'''
SPLASH_BRAND=f'''<div class="tech tm-powered"><span class="tm-powered-label">Powered by</span>{TM_SVG}</div>'''

for page in paths:
    if not page.exists():
        raise SystemExit(f'Branding target not found: {page}')
    s=page.read_text()

    # Remove stale logo image references before inserting the dependency-free SVG.
    s=re.sub(r'<img\b[^>]*src=["\'][^"\']*tm-solutions-logo\.(?:png|webp)[^"\']*["\'][^>]*>', '', s, flags=re.I)

    if page.name == 'app.html':
        # Replace any previously injected TM block, then any old TECH MANZ block.
        s=re.sub(r'<div\b[^>]*class=["\'][^"\']*tm-powered[^"\']*["\'][^>]*>.*?</div>', BRAND, s, flags=re.I|re.S)
        s=re.sub(r'<p\b[^>]*>\s*(?:⚡\s*)?(?:POWERED BY\s+)?TECH\s*MANZ\s*</p>', BRAND, s, flags=re.I)
        s=re.sub(r'<div\b[^>]*class=["\'][^"\']*powered[^"\']*["\'][^>]*>\s*(?:⚡\s*)?(?:POWERED BY\s+)?TECH\s*MANZ\s*</div>', BRAND, s, flags=re.I)
        s=s.replace('Powered by TECHMANZ','Powered by TM Solutions')
        s=s.replace('POWERED BY TECHMANZ','POWERED BY TM SOLUTIONS')
        s=s.replace('Powered by TECH MANZ','Powered by TM Solutions')
        s=s.replace('POWERED BY TECH MANZ','POWERED BY TM SOLUTIONS')
        s=s.replace('⚡ TECHMANZ','TM Solutions')
        s=s.replace('⚡ TECH MANZ','TM Solutions')
        if 'tm-logo-svg' not in s or 'Powered by' not in s:
            raise SystemExit('TM Solutions app branding was not applied')
    else:
        # Entry splash screen shown before app.html.
        s=re.sub(r'<div\b[^>]*class=["\']tech(?:\s+tm-powered)?["\'][^>]*>.*?</div>', SPLASH_BRAND, s, count=1, flags=re.I|re.S)
        s=s.replace('Powered by TECHMANZ','Powered by TM Solutions')
        s=s.replace('POWERED BY TECHMANZ','POWERED BY TM SOLUTIONS')
        s=s.replace('Powered by TECH MANZ','Powered by TM Solutions')
        s=s.replace('POWERED BY TECH MANZ','POWERED BY TM SOLUTIONS')
        if 'tm-logo-svg' not in s:
            s=s.replace('</body>', SPLASH_BRAND+'</body>', 1)
        if 'tm-logo-svg' not in s:
            raise SystemExit('TM Solutions splash branding was not applied')

    page.write_text(s)
    print('Applied inline TM Solutions powered-by branding to', page)

# Remove every legacy/broken branding asset from the generated live site.
for old in ('techmanz-logo.jpg','tm-solutions-logo.png','tm-solutions-logo.webp'):
    p=root/old
    if p.exists():
        p.unlink()
        print('Removed legacy/broken branding asset',p)

# Make the inline wordmark centered, compact and footer-safe on every screen.
css=root/'mobile-fixes.css'
if css.exists():
    c=css.read_text()
    c=re.sub(r"background-image\s*:\s*url\([^)]*(?:techmanz-logo|tm-solutions-logo)[^)]*\)\s*;?",'background-image:none!important;',c,flags=re.I)
    c += '''\n/* Final TM Solutions inline branding guard */\n.tm-powered,.powered.tm-powered{display:grid!important;justify-items:center!important;align-items:center!important;gap:3px!important;width:100%!important;max-width:220px!important;height:auto!important;min-height:0!important;margin:18px auto 8px!important;padding:0!important;overflow:visible!important;border:0!important;border-radius:0!important;background:none!important;background-image:none!important;box-shadow:none!important;isolation:auto!important;color:#7f9d91!important;font-size:9px!important;line-height:1.2!important;text-align:center!important}\n.tm-powered::before,.tm-powered::after,.powered.tm-powered::before,.powered.tm-powered::after{content:none!important;display:none!important;background:none!important;animation:none!important}\n.tm-powered-label{display:block!important;color:#88a79a!important;font-size:9px!important;line-height:1.2!important;font-weight:800!important;letter-spacing:.14em!important;text-transform:uppercase!important}\n.tm-logo-svg{display:block!important;width:148px!important;max-width:58vw!important;height:auto!important;margin:0 auto!important;overflow:visible!important}\n.settings-brand .tm-powered{margin-top:14px!important;max-width:240px!important}.settings-brand .tm-logo-svg{width:158px!important;max-width:62vw!important}\n.side .tm-powered{margin-top:24px!important}.side .tm-logo-svg{width:130px!important}\n@media(max-width:560px){.tm-logo-svg{width:142px!important}.settings-brand .tm-logo-svg{width:152px!important}}\n'''
    css.write_text(c)

# Remove the old company name from PWA metadata too.
manifest=root/'manifest.webmanifest'
if manifest.exists():
    m=manifest.read_text().replace('Powered by TECHMANZ','Powered by TM Solutions').replace('Powered by TECH MANZ','Powered by TM Solutions')
    manifest.write_text(m)

# Hard failure if any live text/CSS still references the old brand or old logo files.
check='\n'.join(p.read_text(errors='ignore') for p in (root/'app.html',root/'index.html',root/'mobile-fixes.css',root/'manifest.webmanifest') if p.exists())
if re.search(r'TECH\s*MANZ|techmanz-logo|tm-solutions-logo\.(?:png|webp)',check,re.I):
    raise SystemExit('Legacy/broken branding reference still exists in generated live files')
if 'tm-logo-svg' not in check or 'SOLUTIONS' not in check:
    raise SystemExit('Inline TM Solutions logo missing from generated live files')
