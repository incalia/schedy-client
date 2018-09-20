# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

from six import raise_from, text_type
import functools

from .pagination import PageObjectsIterator
from . import errors, encoding
from .compat import json_dumps
from .core import DataEqMixin
import requests


class Trials(DataEqMixin, object):
    def __init__(self, core, project_id, experiment_name):
        self.core = core
        self.project_id = project_id
        self.experiment_name = experiment_name

    def create(self, hyperparameters, metrics=None, status=None, metadata=None):
        if status is None:
            status = Trial.QUEUED
        url = self.core.routes.trials(self.project_id, self.experiment_name)
        content = {
            'hyperparameters': {text_type(k): encoding._scalar_definition(v) for k, v in hyperparameters.items()},
            'status': text_type(status)
        }
        if metrics:
            content['metrics'] = {text_type(k): encoding._float_definition(v) for k, v in metrics.items()}
        if metadata:
            content['metadata'] = {text_type(k): encoding._scalar_definition(v) for k, v in metadata.items()}
        data = json_dumps(content, cls=encoding.JSONEncoder)

        response = self.core.authenticated_request('POST', url, data=data)
        if response.status_code == requests.codes.conflict:
            raise errors.ResourceExistsError(response.text + '\n' + url, response.status_code)
        else:
            errors._handle_response_errors(response)
        try:
            content = dict(response.json())
            id_ = text_type(content['id'])
        except (ValueError, KeyError, TypeError) as e:
            raise_from(errors.ServerError('Response contains invalid JSON dict:\n' + response.text, None), e)
        return Trial(self.core, self.project_id, self.experiment_name, id_,
                     status=status,
                     hyperparameters=hyperparameters,
                     metrics=metrics,
                     metadata=metadata,
                     etag=response.headers.get('ETag'),
                     )

    def get(self, id_):
        url = self.core.routes.trial(self.project_id, self.experiment_name, id_)
        response = self.core.authenticated_request('GET', url)
        errors._handle_response_errors(response)
        try:
            content = dict(response.json())
        except ValueError as e:
            raise_from(errors.ServerError('Response contains invalid JSON dict:\n' + response.text, None), e)
        return Trial._from_description(self.core, content, response.headers.get('ETag'))

    def get_all(self):
        url = self.core.routes.trials(self.project_id, self.experiment_name)
        return PageObjectsIterator(
            reqfunc=functools.partial(self.core.authenticated_request, 'GET', url),
            obj_creation_func=functools.partial(Trial._from_description, self.core, etag=None),
            expected_field='trials'
        )

    def delete(self, id_):
        url = self.core.routes.trial(self.project_id, self.experiment_name, id_)
        response = self.core.authenticated_request('DELETE', url)
        errors._handle_response_errors(response)


class Trial(DataEqMixin, object):
    #: Status of a queued trial. Queued trials are returned when calling :py:meth:`schedy.Experiment.next_trial`.
    QUEUED = 'QUEUED'
    #: Status of a trial that is currently running on a worker.
    RUNNING = 'RUNNING'
    #: Status of trial that was being processed by a worker, but the worker crashed before completing the trial.
    CRASHED = 'CRASHED'
    #: Status of a completed trial.
    DONE = 'DONE'

    def __init__(self, core, project_id, experiment_name, id_, status, hyperparameters, metrics=None, metadata=None, etag=None):
        """
        Represents a trial instance belonging to an experiment. You should not
        need to create it by hand. Use :py:meth:`schedy.Experiment.add_trial`,
        :py:meth:`schedy.Experiment.get_trial`,
        :py:meth:`schedy.Experiment.all_trials` or
        :py:meth:`schedy.Experiment.next_trial` instead.

        Trials object are context managers, that it to say they can be used with
        a ``with`` statement. They will be put in the RUNNING state at the
        start of the with statement, and in the DONE or CRASHED state at the
        end (depending on whether an uncaught exception is raised within the
        ``with`` block). See :py:meth:`schedy.Trial.__enter__` for an example of
        how to use this feature.

        Args:
            trial_id (str): Unique id of the trial.
            experiment (schedy.Experiment): Experiment containing this trial.
            hyperparameters (dict): A dictionnary of hyperparameters values.
            status (str): Trial status. See :ref:`trial_status`.
            results (dict): A dictionnary of results values.
            etag (str): Value of the entity tag sent by the backend.
        """
        self._core = core
        self.project_id = project_id
        self.experiment_name = experiment_name
        self.id_ = id_
        self.status = status
        self.hyperparameters = hyperparameters
        self.metrics = metrics or dict()
        self.metadata = metadata or dict()
        self.etag = etag

    @classmethod
    def _from_description(cls, core, description, etag):
        try:
            project_id = description['project']
            experiment_name = description['experiment']
            id_ = description['id']
            status = text_type(description['status'])
            hyperparameters = {
                name: encoding._from_scalar_definition(value)
                for name, value in description['hyperparameters'].items()
            }
            metrics = {
                name: float(value)
                for name, value in description.get('metrics', dict()).items()
            }
            metadata = {
                name: encoding._from_scalar_definition(value)
                for name, value in description.get('metadata', dict()).items()
            }
            return cls(core,
                       project_id=project_id,
                       experiment_name=experiment_name,
                       id_=id_,
                       status=status,
                       hyperparameters=hyperparameters,
                       metrics=metrics,
                       metadata=metadata,
                       etag=etag,
                       )
        except (ValueError, KeyError, TypeError) as e:
            raise_from(ValueError('Invalid map definition for trial.'), e)

    def update(self, safe=True):
        """
        Updates the trial in the database.

        This function is always called at the end of a ``with`` block.

        Args:
            safe (bool): If true, this operation will make sure not to erase
                any content that would have been put by another Schedy call in
                the meantime. For example, this ensures that no two workers
                overwrite each other's work on this trial because they are working
                in parallel.

        Raises:
            schedy.errors.UnsafeUpdateError: If ``safe`` is ``True`` and the
                trial has been modified by another source since it was
                retrieved.
        """
        headers = dict()
        if safe:
            if self.etag is None:
                raise errors.UnsafeUpdateError('Cannot perform safe update: previous ETag is None.', None)
            else:
                headers['If-Match'] = self.etag
        url = self._core.routes.trial(self.project_id, self.experiment_name, self.id_)
        content = {
            'hyperparameters': {text_type(k): encoding._scalar_definition(v) for k, v in self.hyperparameters.items()},
            'status': text_type(self.status),
        }
        if self.metrics:
            content['metrics'] = {text_type(k): encoding._float_definition(v) for k, v in self.metrics.items()}
        if self.metadata:
            content['metadata'] = {text_type(k): encoding._scalar_definition(v) for k, v in self.metadata.items()}
        data = json_dumps(content, cls=encoding.JSONEncoder)
        response = self._core.authenticated_request('PUT', url, data=data, headers=headers)
        errors._handle_response_errors(response)
        etag = response.headers.get('ETag')
        if etag is not None:
            self.etag = etag

    def try_run(self):
        """
        Try to set the status of the trial as ``RUNNING``, or raise an exception
        if another worker tried to do so before this one.
        """
        self.status = Trial.RUNNING
        self.update()

    def delete(self, ensure=True):
        """
        Deletes this trial from the Schedy service.

        Args:
            ensure (bool): If true, an exception will be raised if the trial was
                deleted before this call.
        """
        url = self._core.routes.trial(self.project_id, self.experiment_name, self.id_)
        if ensure:
            headers = {'If-Match': '*'}
        else:
            headers = dict()
        response = self._core.authenticated_request('DELETE', url, headers=headers)
        errors._handle_response_errors(response)

    def __enter__(self):
        """
        Context manager ``__enter__`` method. Will try to set the trial as
        ``CRASHED`` if the trial has not been modified by another worker
        concurrently.

        Example:

        >>> db = schedy.SchedyDB()
        >>> exp = db.get_experiment('Test')
        >>> with exp.next_trial() as trial:
        >>>     my_train_function(trial)

        If ``my_train_function`` raises an exception, the trial will be marked as
        ``CRASHED``. Otherwise it will be marked as ``DONE``. (See
        py:meth:`Trial.__exit__`.)

        Note that since :py:meth:`schedy.Experiment.next_trial` will always return
        a ``RUNNING`` trial, this method will never raise
        :py:exc:`schedy.errors.UnsafeUpdateError` in this case.
        """
        if self.status != Trial.RUNNING:
            self.try_run()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Context manager ``__exit__`` method. Will try to set the trial status as
        ``CRASHED`` if an exception was raised in the ``with`` block.
        Otherwise, it will try to set the trial status as ``DONE``. It will also
        push all the updates that were made locally to the Schedy service (by
        calling :py:meth:`Trial.update` for you).
        """
        if exc_type is not None:
            self.status = Trial.CRASHED
        else:
            self.status = Trial.DONE
        self.update()
