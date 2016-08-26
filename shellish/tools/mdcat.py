import argparse
import shellish
import sys

mdfile = argparse.FileType('r', encoding='utf-8-sig')


@shellish.autocommand
def mdcat(mdfile:mdfile=sys.stdin):
    """ Pretty print a markdown file. """
    shellish.mdprint(mdfile.read())
