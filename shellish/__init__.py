"""
Public interface.
"""

import importlib

for x in ['shell', 'completer', 'command']:
    module = importlib.import_module('.%s' % x, 'shellish')
    for sym in module.__public__:
        globals()[sym] = getattr(module, sym)
