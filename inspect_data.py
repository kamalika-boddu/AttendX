import sys
sys.path.insert(0, 'backend')
from db import execute_query

rows = execute_query('SELECT id, name, class_name, section FROM students ORDER BY class_name, section, id')
print(f"Total students: {len(rows)}")
for r in rows:
    print(f"{r['id']}: {r['name']} ({r['class_name']}-{r['section']})")
