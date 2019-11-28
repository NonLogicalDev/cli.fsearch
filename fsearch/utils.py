import os
import re

from typing import AnyStr


def path_resolve(*path):
    return os.path.expanduser(os.path.expandvars(os.path.join(*path)))


def natural_sort(key: AnyStr):
    return [
        int(c) if c.isdigit() else c.lower()
        for c in re.split(r"\d+", key)
    ]
