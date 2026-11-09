import os
import re

patterns = [
    r'openrouter\.ai',
    r'base_url',
    r'OpenAI\(',
    r'AsyncOpenAI\(',
    r'ChatOpenAI',
    r'HTTP-Referer',
    r'X-Title',
    r'"openrouter/free"',
    r'"qwen',
    r'"llama',
    r'"gpt',
    r'"gemini',
    r'"claude',
]
combined = re.compile('|'.join(f'({p})' for p in patterns), re.IGNORECASE)
ignore_dirs = {'.git', '__pycache__', '.pytest_cache', '.venv', 'venv', 'brain', '.cache'}

matches = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
    for file in files:
        if file.endswith(('.py', '.env', '.env.example', '.json', '.yaml', '.yml', '.txt', '.sh', '.md')):
            if 'dataset' in root or 'runs' in root or 'schema_report' in file:
                continue
            fpath = os.path.join(root, file)
            if fpath in [
                os.path.join('.', 'graph', 'llm_client.py'),
                os.path.join('.', '.env'),
                os.path.join('.', '.env.example'),
                os.path.join('.', 'graph', 'local_secrets.example.py'),
                os.path.join('.', 'graph', 'local_secrets.py'),
                os.path.join('.', 'scripts', 'audit_llm.py'),
            ]:
                continue
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    for lno, line in enumerate(f, 1):
                        if combined.search(line):
                            matches.append((fpath, lno, line.strip()))
            except Exception:
                pass

print(f"Total occurrences outside llm_client.py / .env / local_secrets: {len(matches)}")
for fpath, lno, line in matches:
    print(f"  {fpath}:{lno}: {line}")

