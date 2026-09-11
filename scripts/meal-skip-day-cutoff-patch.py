from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

for app in paths:
    if not app.exists():
        raise SystemExit(f'App file not found: {app}')
    s=app.read_text()

    # One daily kitchen cutoff: 17:00 UAE time. After this, today's skip option disappears,
    # but tomorrow/future dates remain available.
    s=s.replace("const mealSkipCutoffs={Breakfast:'06:00',Lunch:'10:00',Dinner:'17:00'};",
                "const mealSkipCutoffs={Breakfast:'17:00',Lunch:'17:00',Dinner:'17:00'};const mealSkipDayCutoff='17:00';")
    s=s.replace("function mealCutoffDate(date,meal){return new Date(`${date}T${mealSkipCutoffs[meal]}:00+04:00`)}",
                "function mealCutoffDate(date,meal){return new Date(`${date}T${mealSkipDayCutoff}:00+04:00`)}")
    s=s.replace("function mealSkipOpen(date,meal){const now=uaeClock();if(date>now.date)return true;if(date<now.date)return false;const[h,m]=mealSkipCutoffs[meal].split(':').map(Number);return now.minutes<(h*60+m)}",
                "function mealSkipOpen(date,meal){const now=uaeClock();if(date>now.date)return true;if(date<now.date)return false;const[h,m]=mealSkipDayCutoff.split(':').map(Number);return now.minutes<(h*60+m)}")

    # Default to tomorrow after 5 PM so today's option is no longer presented.
    old="function mealSkipPage(){const role=state.profile.role,date=window._mealSkipDate||uaeDateKey(0);"
    new="function mealSkipPage(){const role=state.profile.role,now=uaeClock(),afterCutoff=now.minutes>=17*60,defaultDate=afterCutoff?uaeDateKey(1):uaeDateKey(0),date=window._mealSkipDate||defaultDate;"
    if old in s:
        s=s.replace(old,new,1)

    # Hide today's quick-select after cutoff and explain clearly to members.
    s=s.replace("<button class=ghost onclick=\"window._mealSkipDate='${uaeDateKey(0)}';render()\">Today</button><button class=ghost onclick=\"window._mealSkipDate='${uaeDateKey(1)}';render()\">Tomorrow</button>",
                "${afterCutoff?'':`<button class=ghost onclick=\"window._mealSkipDate='${uaeDateKey(0)}';render()\">Today</button>`}<button class=ghost onclick=\"window._mealSkipDate='${uaeDateKey(1)}';render()\">Tomorrow</button>")

    s=s.replace("<div class=small>Cutoff ${mealSkipCutoffs[meal]}</div>",
                "<div class=small>Daily skip cutoff 17:00</div>")
    s=s.replace("<div class=small>Cutoff ${mealSkipCutoffs[meal]}</div>",
                "<div class=small>Daily skip cutoff 17:00</div>")

    member_note="<div class=note style=\"margin-top:12px\">Skip Meal changes cooking quantity only. It does not reduce your monthly payment or expense share.</div>"
    if member_note in s and 'Today’s skip closes at 5:00 PM' not in s:
        s=s.replace(member_note,
                    "<div class=note style=\"margin-top:12px\"><b>Today’s skip closes at 5:00 PM.</b> After 5:00 PM, today is locked/hidden because kitchen preparation has started. You can still choose tomorrow or any future date.</div>"+member_note,1)

    # Prevent manually selecting today after cutoff by snapping back to tomorrow.
    guard="function mealSkipDateAllowed(date){const now=uaeClock();return !(date===now.date&&now.minutes>=17*60)}"
    if guard not in s:
        anchor='function mealSkipOpen(date,meal)'
        idx=s.find(anchor)
        if idx<0: raise SystemExit('mealSkipOpen not found')
        end=s.find('\n', idx)
        s=s[:end+1]+guard+'\n'+s[end+1:]
    s=s.replace('onchange="window._mealSkipDate=this.value;render()"',
                'onchange="if(!mealSkipDateAllowed(this.value)){toast(\'Today\'s skip closed at 5:00 PM. Choose tomorrow or another day.\');window._mealSkipDate=uaeDateKey(1)}else window._mealSkipDate=this.value;render()"')

    required=["const mealSkipDayCutoff='17:00'",'Today’s skip closes at 5:00 PM','mealSkipDateAllowed(date)','Daily skip cutoff 17:00','defaultDate=afterCutoff?uaeDateKey(1):uaeDateKey(0)']
    missing=[x for x in required if x not in s]
    if missing:
        raise SystemExit('Day cutoff patch missing: '+', '.join(missing))

    app.write_text(s)
    print(f'Applied 5 PM daily meal skip cutoff to {app}')
