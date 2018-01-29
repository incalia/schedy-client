# -*- coding: utf-8 -*-

import numpy as np

def scalar_to_map(value):
    if np.issubdtype(type(value), np.integer) or np.issubdtype(type(value), np.floating):
        return {'number': float(value)}
    elif np.issubdtype(type(value), np.character):
        return {'string': str(value)}
    try:
        out_val = [float(i) for i in value]
        return {'curve': out_val}
    except (ValueError, TypeError) as e:
        raise ValueError('Unrecognized type for scalar.') from e

def scalar_from_map(data):
    data = dict(data)
    if len(data) != 1:
        raise ValueError('Invalid scalar representation.')
    typename, value = next(iter(data.items()))
    try:
        f = _scalar_type_table[typename]
    except KeyError as e:
        raise ValueError('Invalid scalar type: {}'.format(typename)) from e
    return f(value)

_scalar_type_table = {
    'number': lambda x: float(x),
    'string': lambda x: int(x),
    'curve': lambda x: list(x),
}

