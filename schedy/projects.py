# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import functools
from .core import DataEqMixin
from .pagination import PageObjectsIterator
from .experiments import Experiments
from .compat import json_dumps
from . import errors, encoding
import logging

import requests

logger = logging.getLogger(__name__)


class Projects(DataEqMixin, object):
    def __init__(self, core):
        self._core = core

    def get_all(self):
        return PageObjectsIterator(
            reqfunc=functools.partial(self._core.authenticated_request, 'GET', self._core.routes.projects),
            obj_creation_func=functools.partial(Project._from_description, self._core),
            expected_field='projects'
        )

    def get(self, id_):
        assert len(id_) > 0, 'Project ID cannot be empty'

        url = self._core.routes.project(id_)
        response = self._core.authenticated_request('GET', url)
        errors._handle_response_errors(response)

        return Project._from_description(self._core, response.json())

    def create(self, id_, name):
        url = self._core.routes.projects
        content = {
            'projectID': str(id_),
            'name': str(name),
        }
        data = json_dumps(content, cls=encoding.JSONEncoder)
        response = self._core.authenticated_request('POST', url, data=data)

        if response.status_code == requests.codes.conflict:
            raise errors.ResourceExistsError(response.text + '\n' + url, response.status_code)
        else:
            errors._handle_response_errors(response)
        return Project(self._core, id_, name)

    def delete(self, id_):
        url = self._core.routes.project(id_)
        response = self._core.authenticated_request('DELETE', url)
        errors._handle_response_errors(response)


class Project(DataEqMixin, object):

    def __init__(self, core, id_, name):
        self._core = core
        self.id_ = id_
        self.name = name
        self.experiments = Experiments(self._core, self.id_)

    def create_experiment(self, *args, **kwargs):
        """
        Adds an experiment to the Schedy service. Use this function to create
        new experiments.
        """
        return self.experiments.create(*args, **kwargs)

    def get_experiment(self, name):
        return self.experiments.get(name=name)

    def get_experiments(self):
        return self.experiments.get_all()

    def delete_experiment(self, name):
        url = self._core.routes.experiment(self.id_, name)
        response = self._core.authenticated_request('DELETE', url)
        errors._handle_response_errors(response)

    @classmethod
    def _from_description(cls, core, description):
        return cls(core, description['id'], description['name'])
