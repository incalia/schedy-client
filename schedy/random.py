# -*- coding: utf-8 -*-

class LogUniform(object):
    FUNC_NAME = 'loguniform'

    def __init__(self, base, lowexp, highexp):
        self.base = base
        self.lowexp = lowexp
        self.highexp = highexp

    def args_list(self):
        return [self.base, self.lowexp, self.highexp]

    @classmethod
    def from_args_list(cls, args):
        return cls(*_cast_args(cls, args, [float, float, float]))

class Uniform(object):
    FUNC_NAME = 'uniform'

    def __init__(self, low, high):
        self.low = low
        self.high = high

    def args_list(self):
        return [self.low, self.high]

    @classmethod
    def from_args_list(cls, args):
        return cls(*_cast_args(cls, args, [float, float]))

class Choice(object):
    FUNC_NAME = 'choice'

    def __init__(self, values, weights=None):
        self.values = values
        self.weights = weights

    def args_list(self):
        return [self.values] if self.weights is None else [self.values, self.weights]

    @classmethod
    def from_args_list(cls, args):
        if len(args) > 2:
            raise ValueError('{} takes at most 2 arguments, not {}'.format(cls.FUNC_NAME, len(args)))
        values, = _cast_args(cls, args[:1], [list])
        if len(args) > 1:
            weights, = _cast_args(cls, args[1:], [list])
            return cls(values, weights)
        return cls(values)

class Constant(object):
    FUNC_NAME = 'const'

    def __init__(self, value):
        self.value = value

    def args_list(self):
        return [self.value]

    @classmethod
    def from_args_list(cls, args):
        if len(args) != 1:
            raise ValueError('{} takes 1 argument, not {}'.format(cls.FUNC_NAME, len(args)))
        return cls(args[0])

def _cast_args(distribution, args, args_type):
    if len(args) != len(args_type):
        raise ValueError('{} takes {} argument(s), not {}.'.format(distribution.FUNC_NAME, len(args_type), len(args)))
    new_args = list()
    for arg, arg_type in zip(args, args_type):
        try:
            new_args.append(arg_type(arg))
        except ValueError:
            raise ValueError('{} expected {} argument, received {}.'.format(distribution.FUNC_NAME, arg_type, args))
    return new_args

DISTRIBUTION_TYPES = {cls.FUNC_NAME: cls for cls in (LogUniform, Uniform, Choice, Constant)}
