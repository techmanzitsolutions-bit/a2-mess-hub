from pathlib import Path

app = Path('/tmp/a2-pwa/www/app.html').read_text()
functions = Path('functions/index.js').read_text()
rules = Path('firestore.rules').read_text()

checks = {
    'Admin-managed Auth create': "httpsCallable(functions,'createManagedUser')" in app,
    'Admin-managed Auth update/disable': "httpsCallable(functions,'updateManagedUser')" in app,
    'Admin-managed Auth removal': "httpsCallable(functions,'deleteManagedUser')" in app,
    'Immediate disabled/removed logout': 'Account disabled or removed by Admin' in app,
    'Member expense creation hidden': "state.profile.role==='admin'||state.profile.role==='chef'" in app,
    'Meal skip listener survives cleanup': app.index("state.unsubs.forEach(f=>f());state.unsubs=[];") < app.index("collection(db,'mealSkips')"),
    'Backend requires active Admin': "profile.role!=='admin'||profile.active===false||profile.removed===true" in functions,
    'Backend creates Auth account': 'admin.auth().createUser' in functions,
    'Backend disables Auth account': 'admin.auth().updateUser' in functions and '{disabled}' in functions,
    'Backend deletes Auth account': 'admin.auth().deleteUser' in functions,
    'Rules require explicit active profile': 'profile().active == true' in rules,
    'Member data requires active login': 'match /members/{id} {\n      allow read: if active();' in rules,
    'Expense writes exclude Member': 'allow create: if admin() || chef();' in rules,
    'Reference Members search/filter actions': 'setMemberView' in app and 'Search members…' in app,
    'Reference Inventory search/filter actions': 'setInventoryView' in app and 'Low Stock (' in app,
    'Reference Reports export actions': 'exportMemberReport' in app and 'exportExpenseReport' in app,
}

failed = [name for name, passed in checks.items() if not passed]
for name, passed in checks.items():
    print(f"{'PASS' if passed else 'FAIL'}: {name}")
if failed:
    raise SystemExit('Production security checks failed: ' + ', '.join(failed))
