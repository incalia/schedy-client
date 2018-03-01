# -*- coding: utf-8 -*-

import requests
from urllib.parse import urljoin
import json
import functools
import logging

from . import errors, encoding
from .random import DISTRIBUTION_TYPES
from .jobs import Job, _make_job, _job_from_response
from .pagination import PageObjectsIterator

logger = logging.getLogger(__name__)

def _check_status(status):
    return status in (Experiment.RUNNING, Experiment.DONE)

class Experiment(object):
    #: Status of a running experiment.
    RUNNING = 'RUNNING'
    #: Status of a completed (or paused) experiment.
    DONE = 'DONE'

    def __init__(self, name, status=RUNNING):
        '''
        Base-class for all experiments.

        Args:
            name (str): Name of the experiment. An experience is uniquely
                identified by its name.
            status (str): Status of the experiment. See :ref:`experiment_status`
        '''
        self.name = name
        self.status = status
        self._db = None

    def add_job(self, **kwargs):
        '''
        Adds a new job to this experiment.

        Args:
            hyperparameters (dict): A dictionnary of hyperparameters values.
            status (str): Job status. See :ref:`job_status`. Default: QUEUED.
            quality (float): Quality of this job. Default: 0.
            results (dict): A dictionnary of result values. Default: No results (empty dictionary).

        Returns:
            schedy.Job: The instance of the new job.
        '''
        partial_job = Job(
                job_id=None,
                experiment=None,
                **kwargs)
        assert self._db is not None, 'Experiment was not added to a database'
        url = self._jobs_url()
        map_def = partial_job._to_map_definition()
        data = json.dumps(map_def, cls=encoding.SchedyJSONEncoder)
        response = self._db._authenticated_request('POST', url, data=data)
        errors._handle_response_errors(response)
        return _job_from_response(self, response)

    def next_job(self):
        '''
        Returns a new job to be worked on. This job will be set in the
        ``RUNNING`` state. This function handles everything so that two
        workers never start working on the same job.

        Returns:
            schedy.Job: The instance of the requested job.
        '''
        assert self._db is not None, 'Experiment was not added to a database'
        url = urljoin(self._db._experiment_url(self.name), 'nextjob/')
        job = None
        # Try obtaining a job and running it until we manage to get hold of a
        # job we can indeed run (concurrent trials to run a job can cause us to
        # fail, so try and try again)
        while job is None:
            response = self._db._authenticated_request('GET', url)
            if response.status_code == requests.codes.no_content:
                raise errors.NoJobError('No job left for experiment {}.'.format(self.name), None)
            errors._handle_response_errors(response)
            job = _job_from_response(self, response)
            try:
                job.try_run()
            except errors.UnsafeUpdateError:
                job = None
                logger.debug('Two workers tried to start working on the same job, retrying.', exc_info=True)
        return job

    def all_jobs(self):
        '''
        Retrieves all the jobs belonging to this experiment.

        Returns:
            iterator of :py:class:`schedy.Job`: An iterator over all the jobs of this experiment.
        '''
        assert self._db is not None, 'Experiment was not added to a database'
        url = self._jobs_url()
        return PageObjectsIterator(
            reqfunc=functools.partial(self._db._authenticated_request, 'GET', url),
            obj_creation_func=functools.partial(_make_job, self),
        )

    def get_job(self, job_id):
        '''
        Retrieves a job by id.

        Args:
            job_id (str): Id of the job to retrieve.

        Returns:
            schedy.Job: Instance of the requested job.
        '''
        assert self._db is not None, 'Experiment was not added to a database'
        url = self._db._job_url(self.name, job_id)
        response = self._db._authenticated_request('GET', url)
        errors._handle_response_errors(response)
        job = _job_from_response(self, response)
        return job

    def __str__(self):
        try:
            return '{}(name={!r}, params={})'.format(self.__class__.__name__, self.name, self._get_params())
        except NotImplementedError:
            return '{}(name={!r})'.format(self.__class__.__name__, self.name)

    def push_updates(self):
        '''
        Push all the updates made to this experiment to the service.
        '''
        assert self._db is not None, 'Experiment was not added to a database'
        url = self._db._experiment_url(self.name)
        content = self._to_map_definition()
        data = json.dumps(content, cls=encoding.SchedyJSONEncoder)
        response = self._db._authenticated_request('PUT', url, data=data)
        errors._handle_response_errors(response)

    def delete(self, ensure=True):
        '''
        Deletes this experiment.

        Args:
            ensure (bool): If true, an exception will be raised if the experiment was
                deleted before this call.
        '''
        assert self._db is not None, 'Experiment was not added to a database'
        url = self._db._experiment_url(self.name)
        if ensure:
            headers = {'If-Match': '*'}
        else:
            headers = dict()
        response = self._db._authenticated_request('DELETE', url, headers=headers)
        errors._handle_response_errors(response)

    @classmethod
    def _create_from_params(cls, name, status, params):
        raise NotImplementedError()

    def _get_params(self):
        raise NotImplementedError()

    def _to_map_definition(self):
        try:
            scheduler = self.SCHEDULER_NAME
        except AttributeError as e:
            raise AttributeError('Experiment implementations should define a SCHEDULER_NAME attribute') from e
        return {
                'status': self.status,
                'scheduler': {scheduler: self._get_params()},
            }

    @staticmethod
    def _from_map_definition(schedulers, map_def):
        try:
            name = str(map_def['name'])
            status = str(map_def['status'])
            scheduler_def_map = dict(map_def['scheduler'])
            if len(scheduler_def_map) != 1:
                raise ValueError('Invalid scheduler definition: {}.'.format(scheduler_def_map))
            sched_def_key, sched_def_val = next(iter(scheduler_def_map.items()))
            scheduler = str(sched_def_key)
            params = sched_def_val
        except (ValueError, KeyError) as e:
            raise ValueError('Invalid map definition for experiment.') from e
        if not _check_status(status):
            raise ValueError('Invalid or unknown status value: {}.'.format(status))
        try:
            exp_type = schedulers[scheduler]
        except KeyError as e:
            raise ValueError('Invalid or unregistered scheduler name: {}.'.format(scheduler))
        return exp_type._create_from_params(
                name=name,
                status=status,
                params=params)

    def _jobs_url(self):
        return urljoin(self._db._experiment_url(self.name), 'jobs/')

class ManualSearch(Experiment):
    '''
    Inherits :py:class:`schedy.Experiment`. Represents a manual search, that
    is to say an experiment for which the only jobs returned by
    :py:meth:`schedy.Experiment.next_job` are jobs that were queued beforehand
    (by using :py:meth:`schedy.Experiment.add_job` for example).
    '''
    SCHEDULER_NAME = 'Manual'

    @classmethod
    def _create_from_params(cls, name, status, params):
        if params is not None:
            raise ValueError('Expected no parameters for manual search, found {}.'.format(type(params)))
        return cls(name=name, status=status)

    def _get_params(self):
        return None

class RandomSearch(Experiment):
    SCHEDULER_NAME = 'RandomSearch'

    def __init__(self, name, distributions, status=Experiment.RUNNING):
        '''
        Inherits :py:class:`schedy.Experiment`. Represents a random search, that
        is to say en experiment that returns jobs with random hyperparameters when
        no job was queued manually using :py:meth:`schedy.Experiment.add_job`.

        If you create a job manually for this experiment, it must have only and
        all the parameters specified in the ``distributions`` parameter.

        Args:
            name (str): Name of the experiment. An experience is uniquely
                identified by its name.
            distributions (dict): A dictionary of distributions (see
                :py:mod:`schedy.random`), whose keys are the names of the
                hyperparameters.
            status (str): Status of the experiment. See :ref:`experiment_status`
        '''
        super().__init__(name, status)
        self.distributions = distributions

    @classmethod
    def _create_from_params(cls, name, status, params):
        try:
            items = params.items()
        except AttributeError as e:
            raise ValueError('Expected parameters as a dict, found {}.'.format(type(params)))
        distributions = dict()
        for key, dist_def in items:
            try:
                dist_name_raw, dist_args = next(iter(dist_def.items()))
                dist_name = str(dist_name_raw)
            except (KeyError, TypeError) as e:
                raise ValueError('Invalid distribution definition.') from e
            try:
                dist_type = DISTRIBUTION_TYPES[dist_name]
            except KeyError as e:
                raise ValueError('Invalid or unknown distribution type: {}.'.format(dist_name))
            distributions[key] = dist_type._from_args(dist_args)
        return cls(name=name, distributions=distributions, status=status)

    def _get_params(self):
        return {key: {dist.FUNC_NAME: dist._args()} for key, dist in self.distributions.items()}

def _make_experiment(db, data):
    try:
        exp_data = dict(data)
    except ValueError as e:
        raise errors.UnhandledResponseError('Expected experience data as a dict, received {}.'.format(type(data)), None) from e
    try:
        exp = Experiment._from_map_definition(db._schedulers, exp_data)
    except ValueError as e:
        raise errors.UnhandledResponseError('Response contains an invalid experiment', None) from e
    exp._db = db 
    return exp

