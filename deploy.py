"""
Deploy this package to PyPi.

If the package is already uploaded (by --version) then this will do nothing.
Reqires Python3.
"""

import http.client
import json
import subprocess


def setup(*args):
    o = subprocess.check_output('python3 ./setup.py %s' % ' '.join(args),
                                shell=True)
    return o.decode().rstrip()

name = setup('--name')
version = setup('--version')

print("Package:", name)
print("Version:", version)

print("Checking PyPi...")
piconn = http.client.HTTPSConnection('pypi.python.org')
piconn.request("GET", '/pypi/%s/json' % name)
piresp = piconn.getresponse()
if piresp.status != 200:
    exit('PyPi Service Error: %s' % piresp.reason)
piinfo = json.loads(piresp.read().decode())

deployed_versions = list(piinfo['releases'].keys())
if version in deployed_versions:
    print("PyPi is already up-to-date for:", version)
    exit()

print(setup('sdist', 'upload'))
