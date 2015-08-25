"""
Debugging (printf mostly) facilities for the framework.
"""

import pprint

LOG_FILE = 'shellish.debug'


def log(*args):
    formatted = [pprint.pformat(x, width=1) if isinstance(x, (list, dict))
                 else str(x) for x in args]
    with open(LOG_FILE, 'a') as f:
        f.write(' '.join(formatted) + '\n')
