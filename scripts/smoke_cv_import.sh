#!/usr/bin/env bash
set -euo pipefail
TOKEN=$(docker exec jobhunter-api-1 python -c "from app.core.security import create_access_token; print(create_access_token({'sub':'1','email':'ali.sadikincom85@gmail.com'}))")
curl -sS -X POST https://jobs.alisadikinma.com/api/cv/master/import-url \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://alisadikinma.com/en"}' \
  --max-time 240 \
  -o /tmp/cv_import_result.json \
  -w "HTTP %{http_code} (%{time_total}s)\n"
python3 <<'PY'
import json
d = json.load(open('/tmp/cv_import_result.json'))
if 'detail' in d:
    print('ERROR:', d.get('detail'))
else:
    c = d.get('content', {})
    basics = c.get('basics', {})
    print('NAME:', basics.get('name'))
    print('EMAIL:', basics.get('email'))
    print('WORK count:', len(c.get('work') or []))
    print('PROJECTS count:', len(c.get('projects') or []))
    sk = c.get('skills') or {}
    flat = [s for cat,arr in sk.items() for s in (arr or [])]
    print('SKILLS count:', len(flat))
    print('SKILL CATEGORIES:', list(sk.keys()))
    print('FIRST 12 SKILLS:', flat[:12])
PY
