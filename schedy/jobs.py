# -*- coding: utf-8 -*-

import json
import requests
from . import scalars
from . import errors

STATUS_RUNNING = 0
STATUS_CRASHED = 1
STATUS_DONE = 2

def _check_status(status):
    return status in (STATUS_RUNNING, STATUS_CRASHED, STATUS_DONE)

class Job(object):
    def __init__(self, job_id, experiment, status, hyperparameters, results=None):
        self.job_id = job_id
        self.experiment = experiment
        self.status = status
        self.hyperparameters = hyperparameters
        self.results = results

    def __str__(self):
        return '{}(id={!r}, experiment={!r}, hyperparameters={!r})'.format(self.__class__.__name__, self.job_id, self.experiment.name, self.hyperparameters)

    def put(self):
        db = self.experiment._db
        url = db._job_url(self.experiment.name, self.job_id)
        map_def = self._to_map_definition()
        data = json.dumps(map_def)
        response = db._authenticated_request('PUT', url, data=data)
        errors._handle_response_errors(response)

    def __enter__(self):
        self.status = STATUS_RUNNING
        self.put()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            self.status = STATUS_CRASHED
        else:
            self.status = STATUS_DONE
        self.put()

    @classmethod
    def _from_map_definition(cls, experiment, map_def):
        try:
            job_id = str(map_def['id'])
            experiment_name = str(map_def['experiment'])
            status = int(map_def['status'])
            hyperparameters = map_def.get('hyperparameters')
            if hyperparameters is not None:
                hyperparameters = dict(hyperparameters)
            else:
                hyperparameters = dict()
            results = map_def.get('results')
            if results is not None:
                results = {key: scalars.scalar_from_map(val) for key, val in dict(results).items()}
            else:
                results = dict()
        except (KeyError, ValueError) as e:
            raise ValueError('Invalid job map definition.') from e
        if experiment_name != experiment.name:
            raise ValueError('Inconsistent experiment name for job: expected {}, found {}.'.format(experiment.name, experiment_name))
        if not _check_status(status):
            raise ValueError('Invalid or unknown status value: {}.'.format(status))
        return cls(
                job_id=job_id,
                experiment=experiment,
                status=status,
                hyperparameters=hyperparameters,
                results=results)

    def _to_map_definition(self):
        map_def = {
                'id': self.job_id,
                'experiment': self.experiment.name,
                'status': self.status,
            }
        if len(self.hyperparameters) > 0:
            map_def['hyperparameters'] = self.hyperparameters
        if len(self.results) > 0:
            map_def['results'] = {key: scalars.scalar_to_map(val) for key, val in self.results.items()}
        return map_def

