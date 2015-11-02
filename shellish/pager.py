"""
Support for directing output to a pager and then restoring tty state.
"""

import contextlib
import fcntl
import subprocess
import sys
import termios


@contextlib.contextmanager
def tty_restoration(file=None):
    if file is None:
        file = sys.stdout
    assert file.isatty()
    tcsave = termios.tcgetattr(file)
    fcsave = fcntl.fcntl(file, fcntl.F_GETFL)
    try:
        yield
    finally:
        fcntl.fcntl(file, fcntl.F_SETFL, fcsave)
        termios.tcsetattr(file, termios.TCSADRAIN, tcsave)


def pager_process(pager, stdout=None, stderr=None):
    if stdout is None:
        stdout = sys.stdout
    if stderr is None:
        stderr = sys.stderr
    p = subprocess.Popen(pager, shell=True, universal_newlines=True, bufsize=1,
                         stdin=subprocess.PIPE, stdout=stdout, stderr=stderr)
    p.stdin.isatty = stdout.isatty  # Tell others they can do ttyisms.
    return p


@contextlib.contextmanager
def pager_redirect(pager, file=None):
    """ Redirect output to file/stdout to a pager process.  Care is taken to
    restore the controlling tty stdio files to their original state. """
    if file is None:
        file = sys.stdout
    if not pager or not file.isatty():
        yield
        return
    with tty_restoration():
        p = pager_process(pager)
        stdout_save = sys.stdout
        sys.stdout = p.stdin
        try:
            print("START YIELD", file=sys.stderr)
            yield
            print("END YIELD", file=sys.stderr)
        finally:
            print("REDIR FINALLY", file=sys.stderr)
            sys.stdout = stdout_save
            try:
                p.stdin.close()
            except BrokenPipeError:
                print("PIPE CRACK", file=sys.stderr)
                pass
            print("CHWCK RUN ll", p.poll(), file=sys.stderr)
            while p.poll() is None:
                import time
                print(time.time(), 'poolllll', file=sys.stderr)
                try:
                    p.wait()
                except KeyboardInterrupt:
                    print("CTRL C LATER mf", file=sys.stderr)
            print("DONEDONE RUN ll", file=sys.stderr)
