# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import json

def json_dumps(*args, **kwargs):
    return str(json.dumps(*args, **kwargs))

