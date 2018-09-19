# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import functools
from .pagination import PageObjectsIterator
from .experiments import Experiments
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
            obj_creation_func=functools.partial(Project._from_description, self.core),
            expected_field='projects'
        )

    def get(self, id_):
        assert len(id_) > 0, 'Project ID cannot be empty'

        url = self.core.routes.project(id_)
        response = self.core.authenticated_request('GET', url)
        errors._handle_response_errors(response)

        return Project._from_description(self.core, response.json())

    def create(self, id_, name):
        url = self.core.routes.projects
        content = {
            'projectID': str(id_),
            'name': str(name),
        }
        data = json_dumps(content, cls=encoding.SchedyJSONEncoder)
        response = self.core.authenticated_request('POST', url, data=data)

        if response.status_code == requests.codes.conflict:
            raise errors.ResourceExistsError(response.text + '\n' + url, response.status_code)
        else:
            errors._handle_response_errors(response)
        return Project(self.core, id_, name)

    def delete(self, id_):
        url = self.core.routes.project(id_)
        response = self.core.authenticated_request('DELETE', url)
        errors._handle_response_errors(response)


class Project(object):

    def __init__(self, core, id_, name):
        self.core = core
        self.id_ = id_
        self.name = name
        self.experiments = Experiments(self.core, self.id_)

    def create_experiment(self, *args, **kwargs):
        """
        Adds an experiment to the Schedy service. Use this function to create
        new experiments.
        """
        return self.experiments.create(*args, **kwargs)

    def get_experiment(self, name):
        return self.experiments.get(name=name)

    def delete_experiment(self, name):
        url = self.core.routes.experiment(self.id_, name)
        response = self.core.authenticated_request('DELETE', url)
        errors._handle_response_errors(response)

    def get_experiments(self):
        return self.experiments.get_all()

    @classmethod
    def _from_description(cls, core, description):
        return cls(core, description['id'], description['name'])
