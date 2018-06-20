# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

#: Minimize the objective
MINIMIZE = 'min'
#: Maximize the objective
MAXIMIZE = 'max'

class Truncate(object):
    _EXPLOIT_STRATEGY_NAME = 'truncate'

    def __init__(self, proportion=0.2):
        '''
        Truncate exploit strategy: if the selected candidate job is in the
        worst n%, use a candidate job in the top n% instead.

        Args:
            proportion (float): Proportion of jobs that are considered to be
                "best" jobs, and "worst" jobs. For example, if ``proportion =
                0.2``, if the selected candidate job is in the bottom 20%, it
                will be replaced by a job in the top 20%. Must satisfy ``0 <
                proportion <= 0.5``.
        '''
        self.proportion = proportion

    def _get_params(self):
        return self.proportion

    @classmethod
    def _from_params(cls, params):
        proportion = float(params)
        return cls(proportion)

    def __eq__(self, other):
        return type(self) == type(other) and \
            self.proportion == other.proportion

class Perturb(object):
    _EXPLORE_STRATEGY_NAME = 'perturb'

    def __init__(self, min_factor=0.8, max_factor=1.2):
        '''
        Perturb explore strategy: multiply the designated hyperparameter by a
        random factor, sampled from a uniform distribution.

        Args:
            min_factor (float): Minimum value for the factor (inclusive).
            max_factor (float): Maximum value for the factor (exclusive).
        '''
        self.min_factor = min_factor
        self.max_factor = max_factor

    def _get_params(self):
        return {
            'minFactor': float(self.min_factor),
            'maxFactor': float(self.max_factor),
        }

    @classmethod
    def _from_params(cls, params):
        min_factor = float(params['minFactor'])
        max_factor = float(params['maxFactor'])
        return cls(min_factor, max_factor)

    def __eq__(self, other):
        return type(self) == type(other) and \
            self.min_factor == other.min_factor and \
            self.max_factor == other.max_factor

_EXPLOIT_STRATEGIES = {strat._EXPLOIT_STRATEGY_NAME: strat for strat in [
    Truncate
]}

_EXPLORE_STRATEGIES = {strat._EXPLORE_STRATEGY_NAME: strat for strat in [
    Perturb
]}

