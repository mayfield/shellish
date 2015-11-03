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


def pager_process(pagercmd, stdout=None, stderr=None):
    if stdout is None:
        stdout = sys.stdout
    if stderr is None:
        stderr = sys.stderr
    return subprocess.Popen(pagercmd, shell=True, universal_newlines=True,
                            bufsize=1, stdin=subprocess.PIPE, stdout=stdout,
                            stderr=stderr)


@contextlib.contextmanager
def pager_redirect(pagercmd=None, enabled=True, istty=None, file=None):
    """ Redirect output to file/stdout to a pager process.  Care is taken to
    restore the controlling tty stdio files to their original state. """
    if file is None:
        file = sys.stdout
    if not enabled or not pagercmd or not file.isatty():
        yield
        return
    with tty_restoration():
        p = pager_process(pagercmd)
        if istty is None:
            p.stdin.isatty = file.isatty
        else:
            p.stdin.isatty = lambda: istty
        stdout_save = sys.stdout
        sys.stdout = p.stdin
        import time # XXX
        t = time.monotonic
        try:
            print(t(), "START YIELD", file=sys.stderr)
            yield
            print(t(), "END YIELD", file=sys.stderr)
        finally:
            print(t(), "REDIR FINALLY", file=sys.stderr)
            sys.stdout = stdout_save
            try:
                p.stdin.close()
            except BrokenPipeError:
                print(t(), "PIPE CRACK", file=sys.stderr)
                pass
            print(t(), "CHWCK RUN ll", p.poll(), file=sys.stderr)
            while p.poll() is None:
                print(t(), 'poolllll', file=sys.stderr)
                try:
                    p.wait()
                except KeyboardInterrupt:
                    print(t(), "CTRL C LATER mf", file=sys.stderr)
            print(t(), "DONEDONE RUN ll", file=sys.stderr)
