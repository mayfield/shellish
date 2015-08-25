"""
Public interface.
"""

from . import shell, completer, command


def export(module, symbol):
    globals()[symbol] = getattr(module, symbol)

for x in shell.__public__:
    export(shell, x)
for x in completer.__public__:
    export(completer, x)
for x in command.__public__:
    export(command, x)
