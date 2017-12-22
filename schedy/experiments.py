# -*- coding: utf-8 -*-

import requests
from urllib.parse import urljoin
import json

from . import errors
from .random import DISTRIBUTION_TYPES
from .jobs import Job

STATUS_RUNNING = 0
STATUS_DONE = 1

class Experiment(object):
    def __init__(self, name, status):
        self.name = name
        self.status = status
        self._db = None

    def next_job(self):
        assert self._db is not None, 'Experiment was not added to a database'
        url = urljoin(self._db._experiment_url(self.name), 'nextjob/')
        response = requests.get(url)
        if response.status_code == requests.codes.no_content:
            raise errors.NoJobError('No job left for experiment {}.'.format(self.name), None)
        errors._handle_response_errors(response)
        try:
            content = dict(response.json())
        except ValueError as e:
            raise errors.ServerError('Response contains invalid JSON dict:\n' + response.text, None) from e
        try:
            job = Job._from_map_definition(self, content)
        except ValueError as e:
            raise errors.ServerError('Response contains an invalid experiment.', None) from e
        return job

    def all_jobs(self):
        url = urljoin(self._db._experiment_url(self.name), 'jobs/')
        response = requests.get(url)
        errors._handle_response_errors(response)
        try:
            content = list(response.json())
        except ValueError as e:
            raise errors.ServerError('Response contains invalid JSON list:\n' + response.text, None) from e
        jobs = []
        for job_data_raw in content:
            try:
                job_data = dict(job_data_raw)
            except ValueError as e:
                raise errors.ServerError('Excepting the description of a job as a dict, received type {}.'.format(type(job_data_raw)))
            try:
                job = Job._from_map_definition(self, job_data)
            except ValueError as e:
                raise errors.ServerError('Response contains an invalid job.', None) from e
            jobs.append(job)
        return jobs

    def __str__(self):
        try:
            return '{}(name={!r}, params={})'.format(self.__class__.__name__, self.name, self._get_params())
        except:
            return '{}(name={!r})'.format(self.__class__.__name__, self.name)

    def push_updates(self):
        url = self._db._experiment_url(self.name)
        content = self._to_map_definition()
        data = json.dumps(content)
        response = requests.put(url, data=data)
        errors._handle_response_errors(response)

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
                'Status': self.status,
                'SchedulerName': scheduler,
                'SchedulerParams': self._get_params(),
            }

    @staticmethod
    def _from_map_definition(schedulers, map_def):
        try:
            name = str(map_def['Name'])
            status = int(map_def['Status'])
            scheduler = str(map_def['SchedulerName'])
            params = dict(map_def['SchedulerParams'])
        except (ValueError, KeyError) as e:
            raise ValueError('Invalid map definition for experiment.') from e
        try:
            exp_type = schedulers[scheduler]
        except KeyError as e:
            raise ValueError('Invalid or unregistered scheduler name: {}.'.format(scheduler))
        return exp_type._create_from_params(
                name=name,
                status=status,
                params=params)

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
        for key, map_def in items:
            try:
                dist_name = str(map_def['name'])
                dist_args = list(map_def['args'])
            except (KeyError, TypeError) as e:
                raise ValueError('Invalid distribution definition.') from e
            try:
                dist_type = DISTRIBUTION_TYPES[dist_name]
            except KeyError as e:
                raise ValueError('Invalid or unknown distribution type: {}.'.format(dist_name))
            distributions[key] = dist_type.from_args_list(dist_args)
        return cls(name=name, distributions=distributions, status=status)

    def _get_params(self):
        return {key: {'name': dist.FUNC_NAME, 'args': dist.args_list()} for key, dist in self.distributions.items()}

