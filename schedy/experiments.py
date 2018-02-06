# -*- coding: utf-8 -*-

import requests
from urllib.parse import urljoin
import json
import functools

from . import errors
from .random import DISTRIBUTION_TYPES
from .jobs import Job, _make_job
from .pagination import PageObjectsIterator

STATUS_RUNNING = 'RUNNING'
STATUS_DONE = 'DONE'

def _check_status(status):
    return status in (STATUS_RUNNING, STATUS_DONE)

class Experiment(object):
    def __init__(self, name, status=STATUS_RUNNING):
        self.name = name
        self.status = status
        self._db = None

    def next_job(self):
        assert self._db is not None, 'Experiment was not added to a database'
        url = urljoin(self._db._experiment_url(self.name), 'nextjob/')
        response = self._db._authenticated_request('GET', url)
        if response.status_code == requests.codes.no_content:
            raise errors.NoJobError('No job left for experiment {}.'.format(self.name), None)
        errors._handle_response_errors(response)
        try:
            content = dict(response.json())
        except ValueError as e:
            raise errors.UnhandledResponseError('Response contains invalid JSON dict:\n' + response.text, None) from e
        try:
            job = Job._from_map_definition(self, content)
        except ValueError as e:
            raise errors.UnhandledResponseError('Response contains an invalid experiment.', None) from e
        return job

    def all_jobs(self):
        assert self._db is not None, 'Experiment was not added to a database'
        url = urljoin(self._db._experiment_url(self.name), 'jobs/')
        return PageObjectsIterator(
            reqfunc=functools.partial(self._db._authenticated_request, 'GET', url),
            obj_creation_func=functools.partial(_make_job, self),
        )

    def __str__(self):
        try:
            return '{}(name={!r}, params={})'.format(self.__class__.__name__, self.name, self._get_params())
        except NotImplementedError:
            return '{}(name={!r})'.format(self.__class__.__name__, self.name)

    def push_updates(self):
        url = self._db._experiment_url(self.name)
        content = self._to_map_definition()
        data = json.dumps(content)
        response = self._db._perform_request('PUT', url, data=data)
        errors._handle_response_errors(response)

    @classmethod
    def _create_from_params(cls, name, status, params):
        raise NotImplementedError()

    def _get_params(self):
        raise NotImplementedError()

    def _to_map_definition(self):
        try:
            scheduler = self.SCHEDULER_NAME
        except AttributeError as e:
            raise AttributeError('Experiment implementations should define a SCHEDULER_NAME attribute') from e
        return {
                'name': self.name,
                'status': self.status,
                'scheduler': {scheduler: self._get_params()},
            }

    @staticmethod
    def _from_map_definition(schedulers, map_def):
        try:
            name = str(map_def['name'])
            status = str(map_def['status'])
            scheduler_def_map = dict(map_def['scheduler'])
            if len(scheduler_def_map) != 1:
                raise ValueError('Invalid scheduler definition: {}.'.format(scheduler_def_map))
            sched_def_key, sched_def_val = next(iter(scheduler_def_map.items()))
            scheduler = str(sched_def_key)
            params = sched_def_val
        except (ValueError, KeyError) as e:
            raise ValueError('Invalid map definition for experiment.') from e
        if not _check_status(status):
            raise ValueError('Invalid or unknown status value: {}.'.format(status))
        try:
            exp_type = schedulers[scheduler]
        except KeyError as e:
            raise ValueError('Invalid or unregistered scheduler name: {}.'.format(scheduler))
        return exp_type._create_from_params(
                name=name,
                status=status,
                params=params)

class ManualSearch(Experiment):
    SCHEDULER_NAME = 'Manual'

    @classmethod
    def _create_from_params(cls, name, status, params):
        if params is not None:
            raise ValueError('Expected not parameters for manual search, found {}.'.format(type(params)))
        return cls(name=name, status=status)

    def _get_params(self):
        return None

class RandomSearch(Experiment):
    SCHEDULER_NAME = 'RandomSearch'

    def __init__(self, name, distributions, status=STATUS_RUNNING):
        super().__init__(name, status)
        self.distributions = distributions

    @classmethod
    def _create_from_params(cls, name, status, params):
        try:
            items = params.items()
        except AttributeError as e:
            raise ValueError('Expected parameters as a dict, found {}.'.format(type(params)))
        distributions = dict()
        for key, dist_def in items:
            try:
                dist_name_raw, dist_args = next(iter(dist_def.items()))
                dist_name = str(dist_name_raw)
            except (KeyError, TypeError) as e:
                raise ValueError('Invalid distribution definition.') from e
            try:
                dist_type = DISTRIBUTION_TYPES[dist_name]
            except KeyError as e:
                raise ValueError('Invalid or unknown distribution type: {}.'.format(dist_name))
            distributions[key] = dist_type.from_args(dist_args)
        return cls(name=name, distributions=distributions, status=status)

    def _get_params(self):
        return {key: {dist.FUNC_NAME: dist.args()} for key, dist in self.distributions.items()}

def _make_experiment(db, data):
    try:
        exp_data = dict(data)
    except ValueError as e:
        raise errors.UnhandledResponseError('Expected experience data as a dict, received {}.'.format(type(data)), None) from e
    try:
        exp = Experiment._from_map_definition(db._schedulers, exp_data)
    except ValueError as e:
        raise errors.UnhandledResponseError('Response contains an invalid experiment', None) from e
    exp._db = db 
    return exp

