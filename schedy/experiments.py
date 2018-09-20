# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from six import raise_from

import functools
import logging
import requests

from . import errors, encoding
from .compat import json_dumps
from .pagination import PageObjectsIterator
from .trials import Trial
from .core import DataEqMixin

logger = logging.getLogger(__name__)


class Experiments(DataEqMixin, object):
    def __init__(self, core, project_id):
        self.core = core
        self.project_id = project_id

    def create(self, name, hyperparameters, metrics):
        url = self.core.routes.experiments(self.project_id)
        content = {
            'name': str(name),
            'hyperparameters': [{'name': str(paramName)} for paramName in hyperparameters],
            'metricsName': [str(metric) for metric in metrics],
        }
        data = json_dumps(content, cls=encoding.JSONEncoder)
        response = self.core.authenticated_request('POST', url, data=data)
        if response.status_code == requests.codes.conflict:
            raise errors.ResourceExistsError(response.text + '\n' + url, response.status_code)
        else:
            errors._handle_response_errors(response)
        return Experiment(self.core, self.project_id, name,
                          hyperparameters=hyperparameters,
                          metrics=metrics)

    def get(self, name):
        """
            Retrieves an experiment from the Schedy service by name.

            Args:
                name (str): Name of the experiment.

            Returns:
                schedy.Experiment: An experiment of the appropriate type.

        """
        url = self.core.routes.experiment(self.project_id, name)
        response = self.core.authenticated_request('GET', url)
        errors._handle_response_errors(response)
        try:
            content = dict(response.json())
        except ValueError as e:
            raise_from(errors.ServerError('Response contains invalid JSON dict:\n' + response.text, None), e)
        return Experiment._from_description(self.core, content)

    def get_all(self):
        """
        Retrieves all the experiments from the Schedy service.

        Returns:
            iterator of :py:class:`schedy.Experiment`: Iterator over all the experiments.
        """
        return PageObjectsIterator(
            reqfunc=functools.partial(self.core.authenticated_request, 'GET', self.core.routes.experiments(self.project_id)),
            obj_creation_func=functools.partial(Experiment._from_description, self.core),
            expected_field='experiments'
        )

    def delete(self, name):
        url = self.core.routes.experiment(self.project_id, name)
        response = self.core.authenticated_request('DELETE', url)
        errors._handle_response_errors(response)


class Experiment(DataEqMixin, object):
    def __init__(self, core, project_id, name, hyperparameters, metrics):
        self.core = core
        self.project_id = project_id
        self.name = name
        self.hyperparameters = hyperparameters
        self.metrics = metrics

    @classmethod
    def _from_description(cls, core, description):
        try:
            project_id = description['projectID']
            name = description['name']
            hyperparameters = [d['name'] for d in description['hyperparameters']]
            metrics = description['metricsName']

            return cls(core, project_id, name, hyperparameters, metrics)
        except (ValueError, KeyError, TypeError) as e:
            raise_from(ValueError('Invalid map definition for experiment.'), e)

    def create_trial(self, *args, **kwargs):
        return self.trials.create(*args, **kwargs)

    def describe_trial(self, trial_id):
        url = self.core.routes.trial(self.project_id, self.name, trial_id)
        response = self.core.authenticated_request('GET', url)
        return Trial.from_def(response.json())

    def update_trial(self, trial_id, hyperparameters=None, status=None, metrics=None, metadata=None):
        # url = self.core.routes.trial(self.project_id, self.name, trial_id)
        # trial = Trial(self.project_id, self.name, trial_id, hyperparameters, metrics, status, metadata)
        # response = self.core.authenticated_request('PATCH', url, data=trial.to_def().to_json())
        # TODO
        raise NotImplementedError()

    def disable_trial(self, trial_id):
        return self.core.authenticated_request('DELETE', self.core.routes.trial(self.project_id, self.name, trial_id))

    def get_trials(self):
        return PageObjectsIterator(
            reqfunc=functools.partial(self.core.authenticated_request, 'GET', self.core.routes.trials(self.project_id, self.name)),
            obj_creation_func=Trial.from_def,
            expected_field='trials'
        )
