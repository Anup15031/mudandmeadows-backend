from fastapi.testclient import TestClient
import importlib.util
import pathlib

# Load main.py from project root so this script can be run from the scripts/ folder
root = pathlib.Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location("main", str(root / "main.py"))
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)

client = TestClient(main.app)

print('GET /site/site-config.js')
res = client.get('/site/site-config.js')
print(res.status_code)
print(res.text[:500])

print('\nGET /api/programs/wellness')
res = client.get('/api/programs/wellness')
print(res.status_code)
try:
    print(res.json())
except Exception:
    print(res.text)

print('\nGET /programs/debug/collections')
res = client.get('/programs/debug/collections')
print(res.status_code)
try:
    print(res.json())
except Exception:
    print(res.text)

print('\nGET /api/navigation/')
res = client.get('/api/navigation/')
print(res.status_code)
try:
    print(res.json())
except Exception:
    print(res.text)

print('\nGET /navigation/')
res = client.get('/navigation/')
print(res.status_code)
try:
    print(res.json())
except Exception:
    print(res.text)

print('\nGET /api/navigation/?public=false')
res = client.get('/api/navigation/?public=false')
print(res.status_code)
try:
    print(res.json())
except Exception:
    print(res.text)
