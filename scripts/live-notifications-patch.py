from pathlib import Path
import subprocess,sys
p=Path('/tmp/a2-pwa/www/app.html')
s=p.read_text()
marker='</style>'
css='''\n<style id="a2-live-notifications">\n.a2-notify-bell{position:fixed;right:18px;top:16px;z-index:9998;border:1px solid rgba(255,255,255,.15);background:#0c2d25;color:#fff;border-radius:14px;width:46px;height:46px;font-size:21px}.a2-notify-badge{position:absolute;right:-4px;top:-5px;min-width:20px;height:20px;padding:0 5px;border-radius:20px;background:#ef4444;color:#fff;font:700 11px/20px system-ui}.a2-notify-panel{position:fixed;right:16px;top:70px;width:min(390px,calc(100vw - 24px));max-height:70vh;overflow:auto;z-index:9999;background:#09251f;color:#fff;border:1px solid rgba(255,255,255,.13);border-radius:20px;padding:14px}.a2-notify-item{padding:11px 12px;margin:8px 0;border-radius:13px;background:rgba(255,255,255,.07)}@media(max-width:620px){.a2-notify-bell{top:10px;right:10px}.a2-notify-panel{right:8px;top:64px;width:calc(100vw - 16px)}}\n</style>\n'''
if 'id="a2-live-notifications"' not in s:s=s.replace(marker,marker+css,1)
js=r'''<script id="a2-live-notifications-runtime">(()=>{let open=false;function build(){const d=window.state?.data||{},a=[];(d.payments||[]).slice(-15).forEach(x=>a.push(['Payment Received',`${x.memberName||x.name||'Member'} · AED ${Number(x.amount??x.paidAmount??0).toFixed(2)}`]));(d.expenses||[]).slice(-15).forEach(x=>a.push(['Expense Added',`${x.category||x.description||'Expense'} · AED ${Number(x.amount||0).toFixed(2)}`]));let b=document.getElementById('a2NotifyBell');if(!b){b=document.createElement('button');b.id='a2NotifyBell';b.className='a2-notify-bell';b.textContent='🔔';b.onclick=()=>{open=!open;build()};document.body.appendChild(b)}document.getElementById('a2NotifyPanel')?.remove();if(open){let p=document.createElement('div');p.id='a2NotifyPanel';p.className='a2-notify-panel';p.innerHTML='<b>🔔 Live Notifications</b>'+a.reverse().map(x=>`<div class="a2-notify-item"><b>${x[0]}</b><div>${x[1]}</div></div>`).join('');document.body.appendChild(p)}}setInterval(build,5000);setTimeout(build,1200)})();</script>'''
if 'a2-live-notifications-runtime' not in s:s=s.replace('</body>',js+'</body>',1)
p.write_text(s)
# The same deployment step now also enables Firebase Web Push/mobile notification support.
subprocess.run([sys.executable,'scripts/mobile-push-notification-patch.py'],check=True)
print('Added live in-app notifications and Firebase mobile push support')
