"""
A logging handler that's tty aware.
"""

import logging
from . import rendering


class VTMLHandler(logging.StreamHandler):
    """ Parse VTML messages to colorize and embolden logs. """

    def __init__(self, *args, fmt=None, level_prefmt=None, field_prefmt=None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.setFormatter(VTMLFormatter(fmt=fmt, level_prefmt=level_prefmt,
                                        field_prefmt=field_prefmt))

    def format(self, record):
        return str(rendering.vtmlrender(super().format(record)))


class VTMLFormatter(logging.Formatter):

    default_fmt = ' '.join((
        '[%(asctime)s]',
        '[%(name)s]',
        '[%(levelname)s]',
        '%(message)s'
    ))
    default_level_prefmt = {
        logging.DEBUG: '<dim>%s</dim>',
        logging.INFO: '%s',
        logging.WARNING: '<b>%s</b>',
        logging.ERROR: '<red>%s</red>',
        logging.CRITICAL: '<red><b>%s</b></red>',
    }
    default_field_prefmt = {
        "asctime": '<blue>%s</blue>',
        "created": '<blue>%s</blue>',
        "filename": '<magenta>%s</magenta>',
        "funcName": '<yellow>%s</yellow>',
        "lineno": '<cyan>%s</cyan>',
        "name": '<green>%s</green>',
        "process": '<b>%s</b>',
    }

    def __init__(self, fmt=None, field_prefmt=None, level_prefmt=None,
                 **kwargs):
        fmt = fmt or self.default_fmt
        field_prefmt = field_prefmt or self.default_field_prefmt
        self.field_prefmt = dict((k, v) for k, v in field_prefmt.items()
                                 if '%%(%s)' % k in fmt)
        self.level_prefmt = level_prefmt or self.default_level_prefmt
        self.asctime_prefmt = self.field_prefmt.pop('asctime', None)
        super().__init__(fmt=fmt, **kwargs)

    def formatException(self, ei):
        return '\n'.join(rendering.format_exception(ei[1]))

    def formatTime(self, *args, **kwargs):
        s = super().formatTime(*args, **kwargs)
        return self.asctime_prefmt % s

    def usesTime(self):
        return self.asctime_prefmt

    def format(self, record):
        record.levelname = self.level_prefmt[record.levelno] % record.levelname
        for key, fmt in self.field_prefmt.items():
            setattr(record, key, fmt % getattr(record, key))
        return super().format(record)
