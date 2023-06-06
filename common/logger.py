# -*- coding:utf-8 -*-
# @Author: KeyH
# @Date: 2023年6月5日15:57:53

import logging.config
import os

from .const import Const

folder = Const.project_root + "/logs/"
if not os.path.exists(folder):
    os.makedirs(folder)

config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": Const.log_format,
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "DEBUG" if Const.server_debug else "INFO"
        },
        "info_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "formatter": "standard",
            "level": "INFO",
            "filename": folder + "/telegram-client.log",
            "when": "D",
            "interval": 1,
            "encoding": "utf8"
        },
        "error_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "formatter": "standard",
            "level": "ERROR",
            "filename": folder + "/telegram-client.error.log",
            "when": "D",
            "interval": 1,
            "encoding": "utf8"
        }
    },
    "root": {
        "handlers": ["console", "info_file", "error_file"],
        "level": "DEBUG" if Const.server_debug else "INFO",
        "propagate": False
    },
    'loggers': {
        'only_error': {
            'handlers': ["console", "info_file", "error_file"],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

logging.config.dictConfig(config)
Logger = logging.getLogger(__name__)
