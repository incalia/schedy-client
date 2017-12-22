# -*- coding: utf-8 -*-

import requests
from urllib.parse import urljoin

from . import errors
from .random import DISTRIBUTION_TYPES
from .jobs import Job

class Experiment(object):
    def __init__(self, name):
        self.name = name
        self._db = None

    def next_job(self):
        assert self._db is not None, 'Experiment was not added to a database'
        url = urljoin(self._db._experiment_url(self.name), 'nextjob/')
        response = requests.get(url)
        errors._handle_response_errors(response)
        try:
            content = response.json()
        except ValueError as e:
            raise errors.ServerError('Response contains invalid JSON:\n' + response.text, None) from e
        try:
            job = Job._from_map_definition(self, content)
        except ValueError as e:
            raise errors.ServerError('Response contains an invalid experiment.', None) from e
        return job

    def __str__(self):
        try:
            return '{}(name={!r}, params={})'.format(self.__class__.__name__, self.name, self._get_params())
        except:
            return '{}(name={!r})'.format(self.__class__.__name__, self.name)

    @classmethod
    def _create_from_params(cls, name, params):
        raise NotImplementedError()

    def _get_params(self):
        raise NotImplementedError()

    def _to_map_definition(self):
        try:
            scheduler = self.SCHEDULER_NAME
        except AttributeError as e:
            raise AttributeError('Experiment implementations should define a SCHEDULER_NAME attribute') from e
        return {
                'Name': self.name,
                'SchedulerName': scheduler,
                'SchedulerParams': self._get_params(),
            }

    @staticmethod
    def _from_map_definition(schedulers, map_def):
        try:
            name = map_def['Name']
            scheduler = map_def['SchedulerName']
            params = map_def['SchedulerParams']
        except KeyError as e:
            raise ValueError('Invalid map definition for experiment.') from e
        try:
            exp_type = schedulers[scheduler]
        except KeyError as e:
            raise ValueError('Invalid or unregistered scheduler name: {}.'.format(scheduler))
        return exp_type._create_from_params(name, params)

class RandomSearch(Experiment):
    SCHEDULER_NAME = 'RandomSearch'

    def __init__(self, name, distributions):
        super().__init__(name)
        self.distributions = distributions

    @classmethod
    def _create_from_params(cls, name, params):
        try:
            items = params.items()
        except AttributeError as e:
            raise ValueError('Expected parameters as a dict, found {}.'.format(type(params)))
        distributions = dict()
        for key, map_def in items:
            try:
                dist_name = map_def['name']
                dist_args = list(map_def['args'])
            except (KeyError, TypeError) as e:
                raise ValueError('Invalid distribution definition.') from e
            try:
                dist_type = DISTRIBUTION_TYPES[dist_name]
            except KeyError as e:
                raise ValueError('Invalid or unknown distribution type: {}.'.format(dist_name))
            distributions[key] = dist_type.from_args_list(dist_args)
        return cls(name, distributions)

    def _get_params(self):
        return {key: {'name': dist.FUNC_NAME, 'args': dist.args_list()} for key, dist in self.distributions.items()}

