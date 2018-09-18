# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

from six import raise_from
from . import errors, encoding
from .compat import json_dumps


def _check_status(status):
    return status in (Trial.QUEUED, Trial.RUNNING, Trial.CRASHED, Trial.PRUNED, Trial.DONE)


class Trial(object):
    #: Status of a queued trial. Queued trials are returned when calling :py:meth:`schedy.Experiment.next_trial`.
    QUEUED = 'QUEUED'
    #: Status of a trial that is currently running on a worker.
    RUNNING = 'RUNNING'
    #: Status of trial that was being processed by a worker, but the worker crashed before completing the trial.
    CRASHED = 'CRASHED'
    #: Status of a trial that was abandonned because it was not worth working on.
    PRUNED = 'PRUNED'
    #: Status of a completed trial.
    DONE = 'DONE'

    def __init__(self, trial_id, experiment, hyperparameters, status=QUEUED, results=dict(), etag=None):
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
        self.trial_id = trial_id
        self.experiment = experiment
        self.status = status
        self.hyperparameters = hyperparameters
        self.results = results
        self.etag = etag

    def __str__(self):
        return '{}(id={!r}, experiment={!r}, hyperparameters={!r})'.format(self.__class__.__name__, self.trial_id, self.experiment.name, self.hyperparameters)

    def put(self, safe=True):
        """
        Puts a trial in the database, either by creating it or by updating it.

        This function is always called at the end of a ``with`` block.

        Args:
            safe (bool): If true, this operation will make sure not to erase
                any content that would have been put by another Schedy call in
                the meantime. For example, this ensures that no two workers
                overwrite each other's work on this trial because they are working
                in parallel.
        """
        db = self.experiment._db
        url = db._trial_url(self.experiment.name, self.trial_id)
        map_def = self._to_map_definition()
        data = json_dumps(map_def, cls=encoding.SchedyJSONEncoder)
        headers = dict()
        if safe:
            if self.etag is None:
                headers['If-None-Match'] = '*'
            else:
                headers['If-Match'] = self.etag
        response = db._authenticated_request('PUT', url, data=data, headers=headers)
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
        self.put()

    def delete(self, ensure=True):
        """
        Deletes this trial from the Schedy service.

        Args:
            ensure (bool): If true, an exception will be raised if the trial was
                deleted before this call.
        """
        db = self.experiment._db
        url = db._trial_url(self.experiment.name, self.trial_id)
        if ensure:
            headers = {'If-Match': '*'}
        else:
            headers = dict()
        response = db._authenticated_request('DELETE', url, headers=headers)
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
        calling :py:meth:`Trial.put` for you).
        """
        if exc_type is not None:
            self.status = Trial.CRASHED
        else:
            self.status = Trial.DONE
        self.put()

    @classmethod
    def _from_map_definition(cls, experiment, map_def, etag=None):
        try:
            trial_id = str(map_def['id'])
            experiment_name = str(map_def['experiment'])
            status = str(map_def['status'])
            hyperparameters = map_def.get('hyperparameters')
            if hyperparameters is not None:
                hyperparameters = dict(hyperparameters)
            else:
                hyperparameters = dict()
            results = map_def.get('results')
            if results is not None:
                results = dict(results)
            else:
                results = dict()
        except (KeyError, ValueError) as e:
            raise_from(ValueError('Invalid trial map definition.'), e)
        if experiment_name != experiment.name:
            raise ValueError('Inconsistent experiment name for trial: expected {}, found {}.'.format(experiment.name, experiment_name))
        if not _check_status(status):
            raise ValueError('Invalid or unknown status value: {}.'.format(status))
        return cls(
            trial_id=trial_id,
            experiment=experiment,
            status=status,
            hyperparameters=hyperparameters,
            results=results,
            etag=etag
        )

    def _to_map_definition(self):
        map_def = {
            'status': str(self.status),
        }
        if len(self.hyperparameters) > 0:
            map_def['hyperparameters'] = self.hyperparameters
        if self.results is not None and len(self.results) > 0:
            map_def['results'] = self.results
        return map_def


def _make_trial(experiment, data, etag=None):
    try:
        trial_data = dict(data)
    except ValueError as e:
        raise_from(errors.UnhandledResponseError('Excepting the description of a trial as a dict, received type {}.'.format(type(data)), None), e)
    try:
        trial = Trial._from_map_definition(experiment, trial_data, etag)
    except ValueError as e:
        raise_from(errors.UnhandledResponseError('Response contains an invalid trial.', None), e)
    return trial


def _trial_from_response(experiment, response):
    try:
        content = response.json()
    except ValueError as e:
        raise_from(errors.UnhandledResponseError('Response contains invalid JSON:\n' + response.text, None), e)
    return _make_trial(experiment, content, response.headers.get('ETag'))

