from pathlib import Path
import sys

paths=[Path(p) for p in sys.argv[1:]] or [Path('/tmp/a2-pwa/www/app.html')]
if not paths[0].exists() and not sys.argv[1:]:
    paths=[Path('www/app.html')]

for app in paths:
    if not app.exists():
        raise SystemExit(f'App file not found: {app}')
    s=app.read_text()

    # Kitchen routine:
    # - Breakfast can be skipped until 06:00 on the same day.
    # - Dinner is prepared in the evening, so skip closes at 17:00 the same day.
    # - The NEXT DAY'S lunch is prepared together with dinner, so lunch skip closes
    #   at 17:00 on the PREVIOUS day.
    s=s.replace("const mealSkipCutoffs={Breakfast:'06:00',Lunch:'10:00',Dinner:'17:00'};",
                "const mealSkipCutoffs={Breakfast:'06:00',Lunch:'17:00',Dinner:'17:00'};const mealPrepCutoff='17:00';")
    s=s.replace("const mealSkipCutoffs={Breakfast:'17:00',Lunch:'17:00',Dinner:'17:00'};const mealSkipDayCutoff='17:00';",
                "const mealSkipCutoffs={Breakfast:'06:00',Lunch:'17:00',Dinner:'17:00'};const mealPrepCutoff='17:00';")

    old_cutoff="function mealCutoffDate(date,meal){return new Date(`${date}T${mealSkipCutoffs[meal]}:00+04:00`)}"
    old_cutoff2="function mealCutoffDate(date,meal){return new Date(`${date}T${mealSkipDayCutoff}:00+04:00`)}"
    new_cutoff="function mealCutoffDate(date,meal){if(meal==='Lunch'){const d=new Date(`${date}T12:00:00+04:00`);d.setDate(d.getDate()-1);const y=d.getFullYear(),m=String(d.getMonth()+1).padStart(2,'0'),day=String(d.getDate()).padStart(2,'0');return new Date(`${y}-${m}-${day}T${mealPrepCutoff}:00+04:00`)}return new Date(`${date}T${mealSkipCutoffs[meal]}:00+04:00`)}"
    if old_cutoff in s: s=s.replace(old_cutoff,new_cutoff,1)
    if old_cutoff2 in s: s=s.replace(old_cutoff2,new_cutoff,1)

    # Meal-specific availability based on the actual preparation time.
    old_open="function mealSkipOpen(date,meal){const now=uaeClock();if(date>now.date)return true;if(date<now.date)return false;const[h,m]=mealSkipCutoffs[meal].split(':').map(Number);return now.minutes<(h*60+m)}"
    old_open2="function mealSkipOpen(date,meal){const now=uaeClock();if(date>now.date)return true;if(date<now.date)return false;const[h,m]=mealSkipDayCutoff.split(':').map(Number);return now.minutes<(h*60+m)}"
    new_open="function mealSkipOpen(date,meal){return Date.now()<mealCutoffDate(date,meal).getTime()}"
    if old_open in s: s=s.replace(old_open,new_open,1)
    if old_open2 in s: s=s.replace(old_open2,new_open,1)

    # Restore member page to today by default; individual meal cards decide whether the
    # skip action is still available. This lets today's Lunch correctly show as closed
    # while today's Dinner can remain open until 17:00.
    old_page="function mealSkipPage(){const role=state.profile.role,now=uaeClock(),afterCutoff=now.minutes>=17*60,defaultDate=afterCutoff?uaeDateKey(1):uaeDateKey(0),date=window._mealSkipDate||defaultDate;"
    new_page="function mealSkipPage(){const role=state.profile.role,date=window._mealSkipDate||uaeDateKey(0);"
    if old_page in s: s=s.replace(old_page,new_page,1)

    # Always keep Today and Tomorrow selectors. Closed meals themselves no longer offer
    # the skip button, while future meals remain selectable.
    old_buttons="${afterCutoff?'':`<button class=ghost onclick=\"window._mealSkipDate='${uaeDateKey(0)}';render()\">Today</button>`}<button class=ghost onclick=\"window._mealSkipDate='${uaeDateKey(1)}';render()\">Tomorrow</button>"
    new_buttons="<button class=ghost onclick=\"window._mealSkipDate='${uaeDateKey(0)}';render()\">Today</button><button class=ghost onclick=\"window._mealSkipDate='${uaeDateKey(1)}';render()\">Tomorrow</button>"
    if old_buttons in s: s=s.replace(old_buttons,new_buttons,1)

    # Remove the old whole-day guard; availability is now meal-specific.
    import re
    s=re.sub(r"\nfunction mealSkipDateAllowed\(date\)\{[^\n]*\}\n", "\n", s, count=1)
    s=s.replace('onchange="if(!mealSkipDateAllowed(this.value)){toast(\'Today\'s skip closed at 5:00 PM. Choose tomorrow or another day.\');window._mealSkipDate=uaeDateKey(1)}else window._mealSkipDate=this.value;render()"',
                'onchange="window._mealSkipDate=this.value;render()"')

    # Replace old generic cutoff text with kitchen-routine labels.
    s=s.replace("<div class=small>Daily skip cutoff 17:00</div>",
                "<div class=small>${meal==='Lunch'?'Prepared previous evening · cutoff previous day 17:00':meal==='Dinner'?'Cutoff today 17:00':'Cutoff today 06:00'}</div>")
    s=s.replace("<div class=small>Cutoff ${mealSkipCutoffs[meal]}</div>",
                "<div class=small>${meal==='Lunch'?'Prepared previous evening · cutoff previous day 17:00':meal==='Dinner'?'Cutoff today 17:00':'Cutoff today 06:00'}</div>")

    old_note="<div class=note style=\"margin-top:12px\"><b>Today’s skip closes at 5:00 PM.</b> After 5:00 PM, today is locked/hidden because kitchen preparation has started. You can still choose tomorrow or any future date.</div>"
    new_note="<div class=note style=\"margin-top:12px\"><b>Kitchen timing:</b> Dinner and the next day’s Lunch are prepared together in the evening. Dinner must be skipped before 5:00 PM that day; Lunch must be skipped before 5:00 PM on the previous day. Closed meals do not show a Skip option. Future dates remain available.</div>"
    if old_note in s: s=s.replace(old_note,new_note,1)

    required=["const mealPrepCutoff='17:00'","meal==='Lunch'","d.setDate(d.getDate()-1)","Date.now()<mealCutoffDate(date,meal).getTime()","Dinner and the next day’s Lunch are prepared together","Prepared previous evening"]
    missing=[x for x in required if x not in s]
    if missing:
        raise SystemExit('Kitchen cutoff patch missing: '+', '.join(missing))

    app.write_text(s)
    print(f'Applied dinner + next-day lunch preparation cutoffs to {app}')
