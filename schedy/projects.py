# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import functools
from .pagination import PageObjectsIterator
from .experiments import Experiments, Experiment
from .compat import json_dumps
from . import errors, encoding
import logging

import requests

logger = logging.getLogger(__name__)


class Projects(object):
    def __init__(self, core):
        self.core = core

    def get_all(self):
        return PageObjectsIterator(
            reqfunc=functools.partial(self.core.authenticated_request, 'GET', self.core.routes.projects),
            obj_creation_func=functools.partial(Project, self.core),
            expected_field='projects'
        )

    def get(self, project_id):
        project_desc = self.describe(project_id)
        return Project(self.core, project_desc)

    def create(self, project_id, project_name):
        url = self.core.routes.projects
        content = {
            'projectID': project_id,
            'name': project_name
        }

        data = json_dumps(content, cls=encoding.SchedyJSONEncoder)
        response = self.core.authenticated_request('POST', url, data=data)
        # Handle code 412: Precondition failed

        if response.status_code == requests.codes.precondition_failed:
            raise errors.ResourceExistsError(response.text + '\n' + url, response.status_code)
        else:
            errors._handle_response_errors(response)

    def describe(self, project_id):
        assert len(project_id) > 0, 'project_id should be a nonempty string'

        url = self.core.routes.project(project_id)
        response = self.core.authenticated_request('GET', url)
        errors._handle_response_errors(response)

        project_desc = dict(response.json())
        return project_desc

    def disable(self, project_id):
        url = self.core.routes.project(project_id)

        response = self.core.authenticated_request('DELETE', url)
        errors._handle_response_errors(response)

    def __repr__(self):
        return self.get_all()


class Project(object):

    def __init__(self, core, desc):
        self.core = core
        self.desc = desc
        self.id = desc['id']
        self.experiments = Experiments(self.core, self.id)

    def to_def(self):
        return self.desc

    def add_experiment(self, name, params=None, metrics=None):
        """
        Adds an experiment to the Schedy service. Use this function to create
        new experiments.

        Args:
            exp (schedy.Experiment): The experiment to add.

        """

        exp = Experiment(self.core, self.id, name, params, metrics)

        url = self.core.routes.experiments(self.id)

        data = json_dumps(exp.to_def(), cls=encoding.SchedyJSONEncoder)
        response = self.core.authenticated_request('POST', url, data=data)
        # Handle code 412: Precondition failed

        if response.status_code == requests.codes.precondition_failed:
            raise errors.ResourceExistsError(response.text + '\n' + url, response.status_code)
        else:
            errors._handle_response_errors(response)
        exp._db = self

    def get_experiment(self, name):
        self.experiments.get(name=name)

    def delete_experiment(self, name):
        url = self.core.routes.experiment(self.id, name)
        response = self.core.authenticated_request('DELETE', url)
        errors._handle_response_errors(response)

    def get_experiments(self):
        return self.experiments.get_all()
