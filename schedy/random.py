# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

class LogUniform(object):
    _FUNC_NAME = 'loguniform'

    def __init__(self, low, high):
        '''
        LogUniform distribution. Values are sampled betweend ``low`` and ``high``,
        such that ``log(value)`` is uniformly distributed between ``log(low)`` and
        ``log(high)``.

        Args:
            low (float): Minimal value (inclusive).
            high (float): Maximum value (exclusive).
        '''
        self.low = low
        self.high = high

    def _args(self):
        return {
            'low': float(self.low),
            'high': float(self.high),
        }

    @classmethod
    def _from_args(cls, args):
        low = float(args['low'])
        high = float(args['high'])
        return cls(low, high)

    def __eq__(self, other):
        return type(self) == type(other) and \
            self.low == other.low and \
            self.high == other.high

class Uniform(object):
    _FUNC_NAME = 'uniform'

    def __init__(self, low, high):
        '''
        Uniform distribution. Values will be uniformly distributed in the interval [``low``, ``high``).

        Args:
            low (float): Minimal value (inclusive).
            high (float): Maximum value (exclusive).
        '''
        self.low = low
        self.high = high

    def _args(self):
        return {
            'low': float(self.low),
            'high': float(self.high),
        }

    @classmethod
    def _from_args(cls, args):
        low = float(args['low'])
        high = float(args['high'])
        return cls(low, high)

    def __eq__(self, other):
        return type(self) == type(other) and \
            self.low == other.low and \
            self.high == other.high

class Choice(object):
    _FUNC_NAME = 'choice'

    def __init__(self, values, weights=None):
        '''
        Choice distribution. Values will be picked randomly in a set of values. You can optionally provide
        weights for these values, to make some of them more likely to be suggested by
        Schedy than others.

        Args:
            values (list): Possible values that can be picked. They can be
                numbers, strings, booleans, strings, lists or dictionaries, and
                you can mix those.
            weights (list): Weight associated with each value. If provided, the
                length of ``weights`` must be the same as that of ``values``.
        '''
        self.values = values
        self.weights = weights

    def _args(self):
        args = {
            'values': list(self.values),
        }
        if self.weights is not None:
            if len(self.weights) != len(self.values):
                raise ValueError('There must be as many weights as there are values.')
            args['weights'] = [float(weight) for weight in self.weights]
        return args

    @classmethod
    def _from_args(cls, args):
        values = list(args['values'])
        weights = None
        weights_val = args.get('weights')
        if weights_val != None:
            weights = [float(w) for w in weights_val]
        return cls(values, weights)

    def __eq__(self, other):
        return type(self) == type(other) and \
            self.values == other.values and \
            self.weights == other.weights

class Normal(object):
    _FUNC_NAME = 'normal'

    def __init__(self, mean, std):
        '''
        Normal distribution.

        Args:
            mean (float): Desired mean of the distribution.
            std (float): Desired standard deviation of the distribution.
        '''
        self.mean = mean
        self.std = std

    def _args(self):
        return {
            'mean': float(self.mean),
            'std': float(self.std),
        }

    @classmethod
    def _from_args(cls, args):
        mean = float(args['mean'])
        std = float(args['std'])
        return cls(mean, std)

    def __eq__(self, other):
        return type(self) == type(other) and \
            self.mean == other.mean and \
            self.std == other.std

class Constant(object):
    _FUNC_NAME = 'const'

    def __init__(self, value):
        '''
        "Constant" distribution. Will always yield the same value.

        Args:
            value: The value of the samples that will be returned by this
                distribution. Can be a number, string, boolean, string, list or
                dictionary.
        '''
        self.value = value

    def _args(self):
        return self.value

    @classmethod
    def _from_args(cls, args):
        val = args
        return cls(val)

    def __eq__(self, other):
        return type(self) == type(other) and \
            self.value == other.value

_DISTRIBUTION_TYPES = {cls._FUNC_NAME: cls for cls in (LogUniform, Uniform, Choice, Normal, Constant)}
