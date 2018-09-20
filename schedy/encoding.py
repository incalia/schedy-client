# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import base64
from traceback import format_exc
import math
import warnings
import six

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


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        obj = normalize_type(obj)
        return super(JSONEncoder, self).default(obj)


def normalize_type(obj):
    for convert in _additional_convert:
        try:
            val, converted = convert(obj)
            if converted:
                return val
        except Exception:
            warnings.warn(format_exc())
    return obj


def _float_definition(f):
    if f == float('inf'):
        return '+Inf'
    if f == float('-inf'):
        return '-Inf'
    if math.isnan(f):
        return 'NaN'
    return float(f)


def _scalar_definition(obj):
    if obj is None:
        return {'n': None}
    if isinstance(obj, float):
        return {'f': _float_definition(obj)}
    if isinstance(obj, six.integer_types):
        return {'i': obj}
    if isinstance(obj, six.text_type):
        return {'s': obj}
    if isinstance(obj, six.binary_type):
        return {'d': base64.b64encode(obj)}
    if isinstance(obj, bool):
        return {'b': obj}
    if isinstance(obj, dict):
        return {'m': {six.text_type(k): _scalar_definition(v) for k, v in obj.items()}}
    if isinstance(obj, (list, tuple)):
        return {'a': [_scalar_definition(v) for v in obj]}
    raise ValueError('Unsupported scalar type: {}'.format(type(obj)))


def _from_scalar_definition(definition):
    if len(definition) != 1:
        return ValueError('Invalid {type: value} specification for scalar definition:\n{}', definition)
    type_, value = next(iter(definition.items()))
    if type_ == 'n':
        return None
    if type_ == 'f':
        return float(value)
    if type_ == 'i':
        return int(value)
    if type_ == 's':
        return six.text_type(value)
    if type_ == 'd':
        return base64.b64decode(value)
    if type_ == 'b':
        return bool(value)
    if type_ == 'm':
        return {six.text_type(k): _from_scalar_definition(v) for k, v in value.items()}
    if type_ == 'a':
        return [_from_scalar_definition(v) for v in value]
    return ValueError('Unsupported scalar type: {}'.format(type_))

