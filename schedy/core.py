# -*- coding: utf-8 -*-

from .experiments import Experiment, RandomSearch
from . import errors

import json
import requests
from urllib.parse import urljoin

class SchedyDB(object):
    def __init__(self, root):
        self.root = root
        # Add the trailing slash if it's not there
        if len(self.root) == 0 or self.root[-1] != '/':
            self.root = self.root + '/'
        self._schedulers = dict()
        self._register_default_schedulers()

    def add_experiment(self, exp):
        url = self._experiment_url(exp.name)
        content = exp._to_map_definition()
        data = json.dumps(content)
        response = requests.put(url, data=data, headers={'If-None-Match': '*'})
        # Handle code 412: Precondition failed
        if response.status_code == requests.codes.precondition_failed:
            raise errors.ResourceExistsError(response.text, response.status_code)
        else:
            errors._handle_response_errors(response)
        exp._db = self

    def get_experiment(self, name):
        url = self._experiment_url(name)
        response = requests.get(url)
        errors._handle_response_errors(response)
        try:
            content = dict(response.json())
        except ValueError as e:
            raise errors.ServerError('Response contains invalid JSON dict:\n' + response.text, None) from e
        try:
            exp = Experiment._from_map_definition(self._schedulers, content)
        except ValueError as e:
            raise errors.ServerError('Response contains an invalid experiment', None) from e
        exp._db = self
        return exp

    def get_experiments(self):
        url = self._all_experiments_url()
        response = requests.get(url)
        errors._handle_response_errors(response)
        try:
            exp_data_list = list(response.json())
        except ValueError as e:
            raise errors.ServerError('Response contains invalid JSON list:\n' + response.text, None) from e
        experiments = []
        for exp_data_notype in exp_data_list:
            try:
                exp_data = dict(exp_data_notype)
            except ValueError as e:
                raise errors.ServerError('Expected experience data as a dict, received {}.'.format(type(exp_data)))
            try:
                exp = Experiment._from_map_definition(self._schedulers, exp_data)
            except ValueError as e:
                raise errors.ServerError('Response contains an invalid experiment', None) from e
            exp._db = self
            experiments.append(exp)
        return experiments

    def register_scheduler(self, experiment_type):
        self._schedulers[experiment_type.SCHEDULER_NAME] = experiment_type

    def _register_default_schedulers(self):
        self.register_scheduler(RandomSearch)

    def _all_experiments_url(self):
        return urljoin(self.root, 'experiments/')

    def _experiment_url(self, name):
        return urljoin(self._all_experiments_url(), '{}/'.format(name))

    def _job_url(self, job_id):
        return urljoin(self.root, 'jobs/{}/'.format(job_id))

