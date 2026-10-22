from pathlib import Path
import json
p=Path(__file__).resolve().parent
s=(p/'dashboard_template.html').read_text(encoding='utf-8')
d=json.loads((p/'outputs/analysis.json').read_text(encoding='utf-8'))
(p/'outputs/dashboard.html').write_text(s.replace('__ANALYSIS_JSON__',json.dumps(d).replace('</','<\\/')),encoding='utf-8')
print('Built outputs/dashboard.html')
