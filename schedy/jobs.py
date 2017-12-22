# -*- coding: utf-8 -*-

import json
import requests
from . import errors

class Job(object):
    def __init__(self, job_id, experiment, hyperparameters, results=None):
        self.job_id = job_id
        self.experiment = experiment
        self.hyperparameters = hyperparameters
        self.results = results

    def __str__(self):
        return '{}(id={!r}, experiment={!r}, hyperparameters={!r})'.format(self.__class__.__name__, self.job_id, self.experiment.name, self.hyperparameters)

    def update(self):
        db = self.experiment._db
        url = db._job_url(self.job_id)
        map_def = self._to_map_definition()
        data = json.dumps(map_def)
        response = requests.put(url, data=data)
        errors._handle_response_errors(response)

    def __enter__(self):
        self.update()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.update()

    @classmethod
    def _from_map_definition(cls, experiment, map_def):
        try:
            job_id = str(map_def['Id'])
            experiment_name = str(map_def['ExperimentName'])
            hyperparameters = map_def.get('Hyperparameters')
            if hyperparameters is not None:
                hyperparameters = dict(hyperparameters)
            else:
                hyperparameters = dict()
            results = map_def.get('Results')
            if results is not None:
                results = dict(results)
            else:
                results = dict()
        except (KeyError, ValueError) as e:
            raise ValueError('Invalid job map definition.') from e
        if experiment_name != experiment.name:
            raise ValueError('Inconsistent experiment name for job: expected {}, found {}.'.format(experiment.name, experiment_name))
        return cls(job_id, experiment, hyperparameters, results)

    def _to_map_definition(self):
        map_def = {
                'Id': self.job_id,
                'ExperimentName': self.experiment.name,
            }
        if len(self.hyperparameters) > 0:
            map_def['Hyperparameters'] = self.hyperparameters
        if len(self.results) > 0:
            map_def['Results'] = self.results
        return map_def

