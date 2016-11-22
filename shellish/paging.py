"""
Support for directing output to a pager and then restoring tty state.
"""

import contextlib
import fcntl
import os
import shutil
import subprocess
import sys
import termios
import warnings


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
    # When running interactively `less` does not handle window resizes
    # unless we explicitly hardcode the new term size into the env.  There
    # is currently a bug in docker for mac that sometimes breaks this test.
    env = os.environ.copy()
    termsize = shutil.get_terminal_size()
    if 0 in termsize:
        warnings.warn("Could not determine terminal size")
        termsize = os.terminal_size(80, 24)
    env['COLUMNS'] = str(termsize.columns)
    env['LINES'] = str(termsize.lines)
    return subprocess.Popen(pagercmd, shell=True, universal_newlines=True,
                            bufsize=1, stdin=subprocess.PIPE, stdout=stdout,
                            stderr=stderr, env=env)


@contextlib.contextmanager
def pager_redirect(desc, *, pagercmd=None, istty=None, file=None,
                   substitutions=None):
    """ Redirect output to file/stdout to a pager process.  Care is taken to
    restore the controlling tty stdio files to their original state. """
    if file is None:
        file = sys.stdout
    if not pagercmd or not file.isatty():
        yield
        return
    subs = {"desc": desc}
    if substitutions is not None:
        subs.update(substitutions)
    pagercmd = pagercmd.format(**subs)
    with tty_restoration():
        stdout_save = sys.stdout
        p = pager_process(pagercmd)
        try:
            if istty is None:
                p.stdin.isatty = file.isatty
            else:
                p.stdin.isatty = lambda: istty
            sys.stdout = p.stdin
            yield
        finally:
            sys.stdout = stdout_save
            try:
                p.stdin.close()
            except BrokenPipeError:
                pass
            while p.poll() is None:
                try:
                    p.wait()
                except KeyboardInterrupt:
                    pass
