import logging
import os
import sys

import pretty_errors
from colorlog import ColoredFormatter

pretty_errors.configure(
    separator_character='*',
    filename_display=pretty_errors.FILENAME_EXTENDED,
    line_number_first=True,
    display_link=True,
    lines_before=5,
    lines_after=2,
    line_color=pretty_errors.RED + '> ' + pretty_errors.default_config.line_color,
    code_color='  ' + pretty_errors.default_config.line_color,
    truncate_code=True,
    display_locals=True,
    display_trace_locals=True,
    truncate_locals=False,
)


def init_logger(level: str = None, style: str = 'simple') -> None:
    if level is None:
        level = os.getenv('LOG_LEVEL', 'DEBUG')
    change_log_level(level, style)


def get_color_formatter(style: str = 'simple') -> ColoredFormatter:
    if style == 'simple':
        color_format = "%(log_color)s%(levelname)-5s | [%(name)s:%(filename)s:%(lineno)d] " \
                       "%(message)s"
    else:
        color_format = "%(log_color)s[%(process)-2s] %(levelname)-5s | " \
                       "%(name)s:%(filename)s:%(lineno)d - %(message)s"

    color_formatter = ColoredFormatter(color_format,
                                       datefmt=None,
                                       reset=True,
                                       log_colors={
                                           'DEBUG': 'white',
                                           'INFO': 'green',
                                           'WARNING': 'purple',
                                           'ERROR': 'red',
                                           'CRITICAL': 'red,bg_white',
                                       },
                                       secondary_log_colors={},
                                       style='%')
    return color_formatter


def change_log_level(level: str, style: str = 'simple') -> None:
    print('----------------------')
    print('Logger init with level {}'.format(level))
    level = logging.getLevelName(level)

    color_formatter = get_color_formatter(style=style)
    print_handler = logging.StreamHandler(sys.stdout)
    print_handler.setFormatter(color_formatter)
    print_handler.setLevel(level)

    logging.basicConfig(level=logging.DEBUG, handlers=[print_handler])

    logging.info('logging init finished')


def change_default_log_levels() -> None:
    logging.getLogger("oss2.api").setLevel(logging.INFO)
    logging.getLogger("oss2.http").setLevel(logging.INFO)
    logging.getLogger("oss2.auth").setLevel(logging.INFO)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    logging.getLogger("filelock").setLevel(logging.WARNING)
    logging.getLogger('chardet.charsetprober').setLevel(logging.WARNING)
    logging.getLogger("apscheduler.scheduler").setLevel(logging.INFO)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.executors").setLevel(logging.INFO)
    logging.getLogger("elasticsearch").setLevel(logging.INFO)
    logging.getLogger("elasticapm").setLevel(logging.INFO)
    logging.getLogger("elasticapm.transport").setLevel(logging.INFO)
    logging.getLogger("elasticapm.metrics").setLevel(logging.INFO)
    logging.getLogger("elasticapm.conf").setLevel(logging.INFO)
    logging.getLogger("databases").setLevel(logging.INFO)
    logging.getLogger("aio_pika").setLevel(logging.INFO)
    logging.getLogger("pika").setLevel(logging.INFO)
    logging.getLogger("charset_normalizer").setLevel(logging.WARNING)


init_logger(style='simple')
change_default_log_levels()
logger = logging.getLogger('app')

if __name__ == "__main__":
    logging.info('info')
    logging.info('info')
    logging.warning('warning')
    logging.error('error')
