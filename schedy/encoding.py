# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import json
from traceback import format_exc
import warnings

_additional_convert = []

# Only add conversions if the modules exist.
# This way, we do not add unnecessary dependencies
try:
    import numpy as np
    def _np_convert(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist(), True
        if isinstance(obj, np.generic):
            return np.asscalar(obj), True
        return None, False
    _additional_convert.append(_np_convert)
except ImportError:
    pass

class SchedyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        for convert in _additional_convert:
            try:
                val, converted = convert(obj)
                if converted:
                    return val
            except Exception:
                warnings.warn(format_exc())
        return super(SchedyJSONEncoder, self).default(obj)
