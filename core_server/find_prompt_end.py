import sys
sys.stdout.reconfigure(encoding='utf-8')
with open(r'd:\سمير\core_server\app\ai\orchestrator.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if '"""' in line and i > 50:
        print(f'{i+1}: {repr(line[:60])}')
        if i > 70:
            break
