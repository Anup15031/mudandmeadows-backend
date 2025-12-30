import importlib
import traceback
try:
    importlib.import_module('routes.api_compat')
    print('import_ok')
except Exception:
    traceback.print_exc()
    print('import_failed')
