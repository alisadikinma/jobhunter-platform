import json, sys
d = json.load(open('/tmp/cv_r.json'))
c = d.get('content', {})
b = c.get('basics', {})
sk = c.get('skills') or {}
flat = [s for arr in sk.values() for s in (arr or [])]
print('NAME:', b.get('name'))
print('EMAIL:', b.get('email'))
print('WORK:', len(c.get('work') or []))
print('PROJECTS:', len(c.get('projects') or []))
print('SKILLS:', len(flat))
print('CATS:', list(sk.keys()))
print('FIRST_15:', flat[:15])
print('---work positions---')
for w in (c.get('work') or [])[:8]:
    print(' -', w.get('company'), '|', w.get('position'), '|', w.get('startDate'), '->', w.get('endDate'))
print('---first 3 projects---')
for p in (c.get('projects') or [])[:3]:
    print(' -', p.get('name'), '|', (p.get('description') or '')[:80])
