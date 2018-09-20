# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import json
from six import text_type
from requests.compat import quote as urlquote


def json_dumps(*args, **kwargs):
    return text_type(json.dumps(*args, **kwargs))


def uurlquote(arg):
    if isinstance(arg, text_type):
        arg = arg.encode('utf-8')
    return urlquote(arg)

