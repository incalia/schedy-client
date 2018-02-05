# -*- coding: utf-8 -*-

class LogUniform(object):
    FUNC_NAME = 'loguniform'

    def __init__(self, base, lowexp, highexp):
        self.base = base
        self.lowexp = lowexp
        self.highexp = highexp

    def args(self):
        return {
            'base': float(self.base),
            'lowExp': float(self.lowexp),
            'highExp': float(self.highexp),
        }

    @classmethod
    def from_args(cls, args):
        base = float(args['base'])
        lowexp = float(args['lowExp'])
        highexp = float(args['highExp'])
        return cls(base, lowexp, highexp)

class Uniform(object):
    FUNC_NAME = 'uniform'

    def __init__(self, low, high):
        self.low = low
        self.high = high

    def args(self):
        return {
            'low': float(self.low),
            'high': float(self.high),
        }

    @classmethod
    def from_args(cls, args):
        low = float(args['low'])
        high = float(args['high'])
        return cls(low, high)

class Choice(object):
    FUNC_NAME = 'choice'

    def __init__(self, values, weights=None):
        self.values = values
        self.weights = weights

    def args(self):
        args = {
            'values': list(self.values),
        }
        if self.weights is not None:
            if len(self.weights) != len(self.values):
                raise ValueError('There must be as many weights as there are values.')
            args['weights'] = [float(weight) for weight in self.weights]
        return args

    @classmethod
    def from_args(cls, args):
        values = list(args['values'])
        weights = None
        weights_val = args.get('weights')
        if weights_val != None:
            weights = [float(w) for w in weights_val]
        return cls(values, weights)

class Normal(object):
    FUNC_NAME = 'normal'

    def __init__(self, mean, std):
        self.mean = mean
        self.std = std

    def args(self):
        return {
            'mean': float(self.mean),
            'std': float(self.std),
        }

    @classmethod
    def from_args(cls, args):
        mean = float(args['mean'])
        std = float(args['std'])
        return cls(mean, std)

class Constant(object):
    FUNC_NAME = 'const'

    def __init__(self, value):
        self.value = value

    def args(self):
        return self.value

    @classmethod
    def from_args(cls, args):
        val = args
        return cls(val)

DISTRIBUTION_TYPES = {cls.FUNC_NAME: cls for cls in (LogUniform, Uniform, Choice, Constant)}
