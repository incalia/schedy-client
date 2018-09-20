# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from six import raise_from

import functools
import logging
import requests

from . import errors, encoding
from .compat import json_dumps
from .pagination import PageObjectsIterator
from .trials import Trials
from .core import DataEqMixin

logger = logging.getLogger(__name__)


class Experiments(DataEqMixin, object):
    def __init__(self, core, project_id):
        self._core = core
        self.project_id = project_id

    def create(self, name, hyperparameters, metrics):
        url = self._core.routes.experiments(self.project_id)
        content = {
            'name': str(name),
            'hyperparameters': [{'name': str(paramName)} for paramName in hyperparameters],
            'metricsName': [str(metric) for metric in metrics],
        }
        data = json_dumps(content, cls=encoding.JSONEncoder)
        response = self._core.authenticated_request('POST', url, data=data)
        if response.status_code == requests.codes.conflict:
            raise errors.ResourceExistsError(response.text + '\n' + url, response.status_code)
        else:
            errors._handle_response_errors(response)
        return Experiment(self._core, self.project_id, name,
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
        url = self._core.routes.experiment(self.project_id, name)
        response = self._core.authenticated_request('GET', url)
        errors._handle_response_errors(response)
        try:
            content = dict(response.json())
        except ValueError as e:
            raise_from(errors.ServerError('Response contains invalid JSON dict:\n' + response.text, None), e)
        return Experiment._from_description(self._core, content)

    def get_all(self):
        """
        Retrieves all the experiments from the Schedy service.

        Returns:
            iterator of :py:class:`schedy.Experiment`: Iterator over all the experiments.
        """
        return PageObjectsIterator(
            reqfunc=functools.partial(self._core.authenticated_request, 'GET', self._core.routes.experiments(self.project_id)),
            obj_creation_func=functools.partial(Experiment._from_description, self._core),
            expected_field='experiments'
        )

    def delete(self, name):
        url = self._core.routes.experiment(self.project_id, name)
        response = self._core.authenticated_request('DELETE', url)
        errors._handle_response_errors(response)


class Experiment(DataEqMixin, object):
    def __init__(self, core, project_id, name, hyperparameters, metrics):
        self._core = core
        self.project_id = project_id
        self.name = name
        self.hyperparameters = hyperparameters
        self.metrics = metrics
        self.trials = Trials(self._core, self.project_id, self.name)

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

    def get_trial(self, *args, **kwargs):
        return self.trials.get(*args, **kwargs)

    def get_trials(self, *args, **kwargs):
        return self.trials.get_all(*args, **kwargs)

    def delete_trial(self, *args, **kwargs):
        return self.trials.delete(*args, **kwargs)

