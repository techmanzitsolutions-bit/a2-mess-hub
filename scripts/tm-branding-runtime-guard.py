from pathlib import Path

root=Path('/tmp/a2-pwa/www')
if not root.exists(): root=Path('www')
app=root/'app.html'
if not app.exists(): raise SystemExit('app.html not found')
s=app.read_text()

GUARD=r'''
<script id="tm-approved-brand-runtime-guard">
(()=>{
  const APPROVED='./tm-solutions-approved.webp';
  const logo=()=>`<span class="tm-approved-logo-wrap"><img class="tm-approved-logo" src="${APPROVED}" alt="TM Solutions"></span>`;
  const brand=()=>`<span class="tm-powered-label">Powered by</span>${logo()}`;
  let busy=false;
  function enforceApprovedBrand(){
    if(busy)return; busy=true;
    try{
      document.querySelectorAll('.powered,.tm-powered,.tech').forEach(el=>{
        const text=(el.textContent||'').trim().toLowerCase();
        if(el.classList.contains('powered')||el.classList.contains('tm-powered')||text.includes('powered by')||text.includes('techmanz')||text.includes('tech manz')){
          el.classList.add('tm-powered');
          if(!el.querySelector('img.tm-approved-logo') || el.querySelector('img.tm-approved-logo')?.getAttribute('src')!==APPROVED) el.innerHTML=brand();
        }
      });
      document.querySelectorAll('img').forEach(img=>{
        const src=(img.getAttribute('src')||'').toLowerCase();
        const alt=(img.getAttribute('alt')||'').toLowerCase();
        if((src.includes('techmanz')||src.includes('tm-solutions-logo')||alt.includes('tech manz'))&&!img.classList.contains('tm-approved-logo')){
          img.src=APPROVED; img.alt='TM Solutions'; img.className='tm-approved-logo';
        }
      });
    } finally {busy=false}
  }
  document.addEventListener('DOMContentLoaded',enforceApprovedBrand);
  new MutationObserver(()=>requestAnimationFrame(enforceApprovedBrand)).observe(document.documentElement,{subtree:true,childList:true});
  window.enforceApprovedTMBrand=enforceApprovedBrand;
})();
</script>
'''

if 'id="tm-approved-brand-runtime-guard"' not in s:
    s=s.replace('</body>',GUARD+'\n</body>',1)
app.write_text(s)

# Also ensure the splash page uses the same exact approved asset.
index=root/'index.html'
if index.exists():
    i=index.read_text()
    if 'tm-solutions-approved.webp' not in i:
        raise SystemExit('Splash does not reference approved TM logo')

# Final production guardrails.
if s.count('tm-solutions-approved.webp') < 2:
    raise SystemExit('Approved logo is not enforced in app runtime')
if 'MutationObserver' not in s or 'enforceApprovedTMBrand' not in s:
    raise SystemExit('Runtime branding guard missing')
print('Exact approved TM Solutions logo enforced at all powered-by locations, including after login')
