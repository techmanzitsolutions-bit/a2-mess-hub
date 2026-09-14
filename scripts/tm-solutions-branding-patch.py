from pathlib import Path
import re, sys

# Final branding cleanup. Runs after every other UI patch so no legacy branding
# can survive in splash, login, sidebar, settings, footer or responsive CSS.
if sys.argv[1:]:
    paths=[Path(p) for p in sys.argv[1:]]
    root=paths[0].parent
else:
    root=Path('/tmp/a2-pwa/www')
    if not root.exists():
        root=Path('www')
    paths=[root/'app.html', root/'index.html']

ASSET='./tm-solutions-logo.webp?v=3'
BRAND=f'''<div class="powered tm-powered"><span>Powered by</span><img src="{ASSET}" alt="TM Solutions"></div>'''
SPLASH_BRAND=f'''<div class="tech tm-powered"><span>Powered by</span><img src="{ASSET}" alt="TM Solutions"></div>'''

for page in paths:
    if not page.exists():
        raise SystemExit(f'Branding target not found: {page}')
    s=page.read_text()

    # Normalize older TM asset variants to the approved logo.
    s=re.sub(r'\./tm-solutions-logo\.(?:png|webp)(?:\?v=\d+)?', ASSET, s, flags=re.I)

    if page.name == 'app.html':
        # Replace any old text-based powered-by mark.
        s=re.sub(r'<p\b[^>]*>\s*(?:⚡\s*)?(?:POWERED BY\s+)?TECH\s*MANZ\s*</p>', BRAND, s, flags=re.I)
        s=re.sub(r'<div\b[^>]*class=["\'][^"\']*powered[^"\']*["\'][^>]*>\s*(?:⚡\s*)?(?:POWERED BY\s+)?TECH\s*MANZ\s*</div>', BRAND, s, flags=re.I)
        s=s.replace('Powered by TECHMANZ','Powered by TM Solutions')
        s=s.replace('POWERED BY TECHMANZ','POWERED BY TM SOLUTIONS')
        s=s.replace('Powered by TECH MANZ','Powered by TM Solutions')
        s=s.replace('POWERED BY TECH MANZ','POWERED BY TM SOLUTIONS')
        s=s.replace('⚡ TECHMANZ','TM Solutions')
        s=s.replace('⚡ TECH MANZ','TM Solutions')
        if 'tm-solutions-logo.webp?v=3' not in s or 'Powered by' not in s:
            raise SystemExit('TM Solutions app branding was not applied')
    else:
        # Entry splash screen shown before app.html.
        s=re.sub(r'<div\b[^>]*class=["\']tech(?:\s+tm-powered)?["\'][^>]*>.*?</div>', SPLASH_BRAND, s, count=1, flags=re.I|re.S)
        s=s.replace('Powered by TECHMANZ','Powered by TM Solutions')
        s=s.replace('POWERED BY TECHMANZ','POWERED BY TM SOLUTIONS')
        s=s.replace('Powered by TECH MANZ','Powered by TM Solutions')
        s=s.replace('POWERED BY TECH MANZ','POWERED BY TM SOLUTIONS')
        if 'tm-solutions-logo.webp?v=3' not in s:
            s=s.replace('</body>', SPLASH_BRAND+'</body>', 1)
        if 'tm-solutions-logo.webp?v=3' not in s:
            raise SystemExit('TM Solutions splash branding was not applied')

    page.write_text(s)
    print('Applied approved TM Solutions branding to', page)

# Remove every legacy/broken branding asset from the generated live site.
for old in ('techmanz-logo.jpg','tm-solutions-logo.png'):
    p=root/old
    if p.exists():
        p.unlink()
        print('Removed legacy branding asset',p)

# Ensure responsive CSS cannot paint an old background image over the logo.
css=root/'mobile-fixes.css'
if css.exists():
    c=css.read_text()
    c=re.sub(r"background-image\s*:\s*url\([^)]*techmanz-logo[^)]*\)\s*;?",'background-image:none!important;',c,flags=re.I)
    c += '''\n/* Final TM Solutions branding guard */\n.tm-powered,.powered.tm-powered{display:grid!important;justify-items:center!important;align-items:center!important;gap:5px!important;width:auto!important;max-width:100%!important;height:auto!important;min-height:0!important;margin:18px auto 8px!important;padding:0!important;overflow:visible!important;border:0!important;border-radius:0!important;background:none!important;background-image:none!important;box-shadow:none!important;isolation:auto!important;color:#7f9d91!important;font-size:9px!important;line-height:1.2!important;text-align:center!important}\n.tm-powered::before,.tm-powered::after,.powered.tm-powered::before,.powered.tm-powered::after{content:none!important;display:none!important;background:none!important;animation:none!important}\n.tm-powered span,.powered.tm-powered span{display:block!important;color:#7f9d91!important;font-size:9px!important;line-height:1.2!important;letter-spacing:.08em!important;text-transform:uppercase!important}\n.tm-powered img,.powered.tm-powered img{display:block!important;width:116px!important;max-width:52vw!important;height:auto!important;object-fit:contain!important;margin:0 auto!important;border:0!important;border-radius:0!important;background:transparent!important;box-shadow:none!important;filter:drop-shadow(0 0 8px rgba(38,160,255,.30))!important}\n.settings-brand .tm-powered{margin-top:14px!important}.settings-brand .tm-powered img{width:124px!important;max-width:58vw!important}\n@media(max-width:560px){.tm-powered img,.powered.tm-powered img{width:108px!important}.settings-brand .tm-powered img{width:118px!important}}\n'''
    css.write_text(c)

# Remove the old company name from PWA metadata too.
manifest=root/'manifest.webmanifest'
if manifest.exists():
    m=manifest.read_text().replace('Powered by TECHMANZ','Powered by TM Solutions').replace('Powered by TECH MANZ','Powered by TM Solutions')
    manifest.write_text(m)

# Hard failure if any live text/CSS still references the old brand.
check='\n'.join(p.read_text(errors='ignore') for p in (root/'app.html',root/'index.html',root/'mobile-fixes.css',root/'manifest.webmanifest') if p.exists())
if re.search(r'TECH\s*MANZ|techmanz-logo',check,re.I):
    raise SystemExit('Legacy TECH MANZ branding still exists in generated live files')
if not (root/'tm-solutions-logo.webp').exists():
    raise SystemExit('Approved TM Solutions logo asset missing')
