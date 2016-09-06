"""
A logging handler that's tty aware.
"""

import logging
from . import rendering


class VTMLHandler(logging.StreamHandler):
    """ Parse VTML messages to colorize and embolden logs. """

    log_format = '[<blue>%(asctime)s</blue>] [<cyan>%(name)s</cyan>] ' \
        '[%(levelname)s] %(message)s'
    level_fmt = {
        10: '<dim>%s</dim>',
        20: '%s',
        30: '<b>%s</b>',
        40: '<red>%s</red>',
        50: '<red><b>%s</b></red>',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFormatter(VTMLFormatter(self.log_format))

    def format(self, record):
        record.levelname = self.level_fmt[record.levelno] % record.levelname
        return str(rendering.vtmlrender(super().format(record)))


class VTMLFormatter(logging.Formatter):

    def formatException(self, ei):
        return '\n'.join(rendering.format_exception(ei[1]))
