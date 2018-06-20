# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from six import raise_from

import requests
from requests.compat import urljoin
import functools
import logging

from . import errors, encoding
from .random import _DISTRIBUTION_TYPES
from .pbt import _EXPLOIT_STRATEGIES, _EXPLORE_STRATEGIES
from .jobs import Job, _make_job, _job_from_response
from .pagination import PageObjectsIterator
from .compat import json_dumps

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
            name (str): Name of the experiment. An experiment is uniquely
                identified by its name.
            status (str): Status of the experiment. See :ref:`experiment_status`.
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
        data = json_dumps(map_def, cls=encoding.SchedyJSONEncoder)
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
        data = json_dumps(content, cls=encoding.SchedyJSONEncoder)
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
            scheduler = self._SCHEDULER_NAME
        except AttributeError as e:
            raise_from(AttributeError('Experiment implementations should define a _SCHEDULER_NAME attribute'), e)
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
            raise_from(ValueError('Invalid map definition for experiment.'), e)
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
    Represents a manual search, that is to say an experiment for which the only
    jobs returned by :py:meth:`schedy.Experiment.next_job` are jobs that were
    queued beforehand (by using :py:meth:`schedy.Experiment.add_job` for
    example).
    '''
    _SCHEDULER_NAME = 'Manual'

    @classmethod
    def _create_from_params(cls, name, status, params):
        if params is not None:
            raise ValueError('Expected no parameters for manual search, found {}.'.format(type(params)))
        return cls(name=name, status=status)

    def _get_params(self):
        return None

class RandomSearch(Experiment):
    _SCHEDULER_NAME = 'RandomSearch'

    def __init__(self, name, distributions, status=Experiment.RUNNING):
        '''
        Represents a random search, that is to say en experiment that returns
        jobs with random hyperparameters when no job was queued manually using
        :py:meth:`schedy.Experiment.add_job`.

        If you create a job manually for this experiment, it must have only and
        all the hyperparameters specified in the ``distributions`` parameter.

        Args:
            name (str): Name of the experiment. An experiment is uniquely
                identified by its name.
            distributions (dict): A dictionary of distributions (see
                :py:mod:`schedy.random`), whose keys are the names of the
                hyperparameters.
            status (str): Status of the experiment. See :ref:`experiment_status`.
        '''
        super(RandomSearch, self).__init__(name, status)
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
                raise_from(ValueError('Invalid distribution definition.'), e)
            try:
                dist_type = _DISTRIBUTION_TYPES[dist_name]
            except KeyError as e:
                raise ValueError('Invalid or unknown distribution type: {}.'.format(dist_name))
            distributions[key] = dist_type._from_args(dist_args)
        return cls(name=name, distributions=distributions, status=status)

    def _get_params(self):
        return {key: {dist._FUNC_NAME: dist._args()} for key, dist in self.distributions.items()}

class PopulationBasedTraining(Experiment):
    _SCHEDULER_NAME = 'PBT'

    def __init__(self, name, objective, result_name, exploit, explore=dict(), initial_distributions=dict(), population_size=None, status=Experiment.RUNNING, max_generations=None):
        '''
        Implements Population Based Training (see `paper
        <https://arxiv.org/pdf/1711.09846.pdf>`_).

        You have two ways to specify the initial jobs for Population Based
        training. You can create them manually using
        :py:meth:`schedy.Experiment.add_job`, or you can specify the
        ``initial_distributions`` and ``population_size`` parameters.

        If you create a job manually for this experiment, it must have at least
        the hyperparameters specified in the ``explore`` parameter.

        Args:
            name (str): Name of the experiment. An experiment is uniquely
                identified by its name.
            objective (str): The objective of the training, either
                :py:attr:`schedy.pbt.MINIMIZE` (to
                minimize a result) or
                :py:attr:`schedy.pbt.MAXIMIZE` (to
                maximize a result).
            result_name (str): The name of the result to optimize. This result
                must be present in the results of all
                :py:attr:`~schedy.Experiment.RUNNING` jobs of this experiment.
            exploit (schedy.pbt.ExploitStrategy): Strategy to use to
                exploit the results (i.e. to focus on the most promising jobs).
            explore (dict): Strategy to use to explore new hyperparameter values.
                The keys of the dictionary are the name of the
                hyperparameters (str), and the values are the strategy
                associated with the hyperparameter
                (:py:class:`schedy.pbt.ExploreStrategy`). Values for the
                omitted hyperparameters will not be explored. This parameter is
                optional: if you do not specify any explore strategy, only
                exploitation will be used.
            initial_distributions (dict): The initial distributions for the
                hyperparameters, as dictionary of distributions (see
                :py:mod:`schedy.random`) whose keys are the names of the
                hyperparameters. This parameter optional, you can also create
                the initial jobs manually. If you use this parameter, make sure
                to use ``population_size`` as well.
            population_size (int): Number of initial jobs to create, before
                starting to exploit/explore (i.e. size of the population). It
                does **not** have to be the number of jobs you can process in
                parallel. The original paper used values between 10 and 80.
            status (str): Status of the experiment. See :ref:`experiment_status`.
            max_generations (int): Maximum number of generations to run before
                marking the experiment the experiments as done
                (:py:ref:`experiment_status`). When the maximum number of
                generations is reached, subsequent calls to
                :py:meth:`schedy.Experiment.next_job` will raise
                :py:class:`schedy.errors.NoJobError`, to indicate that the job
                queue is empty.
        '''
        super(PopulationBasedTraining, self).__init__(name, status)
        self.objective = objective
        self.result_name = result_name
        self.exploit = exploit
        self.explore = explore
        self.initial_distributions = initial_distributions
        self.population_size = population_size
        self.max_generations = max_generations

    @classmethod
    def _create_from_params(cls, name, status, params):
        kwargs = {
            'name': name,
            'status': status,
            'objective': params['objective'],
            'result_name': params['qualityResultName'],
        }
        exploit_type, exploit_params = next(iter(params['exploit'].items()))
        kwargs['exploit'] = _EXPLOIT_STRATEGIES[exploit_type]._from_params(exploit_params)
        population_size = params.get('numParallel')
        if population_size is not None:
            kwargs['population_size'] = population_size
        initial_distributions = params.get('init')
        if initial_distributions is not None:
            init_param = dict()
            for hp, dist_map in initial_distributions.items():
                dist_name, dist_params = next(iter(dist_map.items()))
                init_param[hp] = _DISTRIBUTION_TYPES[dist_name]._from_args(dist_params)
            kwargs['initial_distributions'] = init_param
        explore = params.get('explore')
        if explore is not None:
            explore_map = dict()
            for hp, strat_map in explore.items():
                strat_name, strat_params = next(iter(strat_map.items()))
                explore_map[hp] = _EXPLORE_STRATEGIES[strat_name]._from_params(strat_params)
            kwargs['explore'] = explore_map
        max_generations = params.get('max_generations')
        if max_generations is not None:
            kwargs['max_generations'] = max_generations
        return cls(**kwargs)

    def _get_params(self):
        params = {
            'objective': self.objective,
            'qualityResultName': self.result_name,
        }
        if self.population_size:
            params['numParallel'] = self.population_size
        if self.initial_distributions:
            params['init'] = {
                name: {dist._FUNC_NAME: dist._args()} for name, dist in self.initial_distributions.items()
            }
        params['exploit'] = {self.exploit._EXPLOIT_STRATEGY_NAME: self.exploit._get_params()}
        if self.explore:
            params['explore'] = {
                name: {strat._EXPLORE_STRATEGY_NAME: strat._get_params()} for name, strat in self.explore.items()
            }
        if self.max_generations:
            params['maxGenerations'] = self.max_generations
        return params

def _make_experiment(db, data):
    try:
        exp_data = dict(data)
    except ValueError as e:
        raise_from(errors.UnhandledResponseError('Expected experiment data as a dict, received {}.'.format(type(data)), None), e)
    try:
        exp = Experiment._from_map_definition(db._schedulers, exp_data)
    except ValueError as e:
        raise_from(errors.UnhandledResponseError('Response contains an invalid experiment', None), e)
    exp._db = db 
    return exp

