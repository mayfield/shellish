import argparse
import csv
import shellish
import sys

csvfile = argparse.FileType('r', encoding='utf-8-sig')


@shellish.autocommand
def csvpretty(csvfile:csvfile=sys.stdin):
    """ Pretty print a CSV file. """
    shellish.tabulate(csv.reader(csvfile))
