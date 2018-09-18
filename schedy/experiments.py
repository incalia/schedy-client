# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from six import raise_from

import functools
import logging
import requests

from . import errors
from .pagination import PageObjectsIterator
from .trials import Trial

logger = logging.getLogger(__name__)


class Experiment(object):
    def __init__(self, core, project_id, name, params, metrics):
        assert params is None or isinstance(params, list)
        assert metrics is None or isinstance(metrics, list)

        self.core = core
        self.name = name
        self.params = list(set(params)) or []
        self.metrics = list(set(metrics)) or []
        self.project_id = project_id

    @classmethod
    def from_def(cls, core, definition):
        try:
            # {'projectID': 'project_000', 'name': 'project_000_exp_000', 'hyperparameters': [{'name': 'layer sizes'}
            project_id = definition['projectID']
            name = definition['name']
            params = [d['name'] for d in definition['hyperparameters']]
            metrics = definition['metricsName']

            return cls(core, project_id, name, params, metrics)
        except (ValueError, KeyError) as e:
            raise_from(ValueError('Invalid map definition for experiment.'), e)

    def add_parameter(self, name):
        if name not in self.params:
            self.params += [{'name': name}]

    def add_metric(self, name):
        if name not in self.metrics:
            self.metrics += [name]

    def to_def(self):
        return {
            'name': self.name,
            'hyperparameters': [{'name': p} for p in self.params],
            'metricsName': self.metrics,
        }

    def create_trial(self, hyperparameters, status=None, metrics=None, metadata=None):
        url = self.core.routes.trials(self.project_id, self.name)
        trial = Trial(self.project_id, self.name, None, hyperparameters, metrics, status, metadata)
        print(trial.to_def().to_json())
        response = self.core.authenticated_request('POST', url, data=trial.to_def().to_json())
        # Handle code 412: Precondition failed

        if response.status_code == requests.codes.precondition_failed:
            raise errors.ResourceExistsError(response.text + '\n' + url, response.status_code)
        else:
            errors._handle_response_errors(response)

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


class Experiments(object):
    def __init__(self, core, project_id):
        self.core = core
        self.project_id = project_id

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
        try:
            # TODO: fix this.
            exp = Experiment(content)
        except ValueError as e:
            raise_from(errors.ServerError('Response contains an invalid experiment', None), e)

        return exp

    def get_all(self):
        """
        Retrieves all the experiments from the Schedy service.

        Returns:
            iterator of :py:class:`schedy.Experiment`: Iterator over all the experiments.
        """
        return PageObjectsIterator(
            reqfunc=functools.partial(self.core.authenticated_request, 'GET', self.core.routes.experiments(self.project_id)),
            obj_creation_func=functools.partial(Experiment.from_def, self.core),
            expected_field='experiments'
        )

# import requests
# from requests.compat import urljoin
# import functools
# import logging
#
# from . import errors, encoding
# from .random import _DISTRIBUTION_TYPES
# from .pbt import _EXPLOIT_STRATEGIES, _EXPLORE_STRATEGIES
# from .trials import Trial, _make_trial, _trial_from_response
# from .pagination import PageObjectsIterator
# from .compat import json_dumps
#
# logger = logging.getLogger(__name__)
#
# def _check_status(status):
#     return status in (Experiment.RUNNING, Experiment.DONE)
#
# class Experiment(object):
#     #: Status of a running experiment.
#     RUNNING = 'RUNNING'
#     #: Status of a completed (or paused) experiment.
#     DONE = 'DONE'
#
#     def __init__(self, name, status=RUNNING):
#         """
#         Base-class for all experiments.
#
#         Args:
#             name (str): Name of the experiment. An experiment is uniquely
#                 identified by its name.
#             status (str): Status of the experiment. See :ref:`experiment_status`.
#         """
#         self.name = name
#         self.status = status
#         self._db = None
#
#     def add_trial(self, **kwargs):
#         """
#         Adds a new trial to this experiment.
#
#         Args:
#             hyperparameters (dict): A dictionnary of hyperparameters values.
#             status (str): Trial status. See :ref:`trial_status`. Default: QUEUED.
#             results (dict): A dictionnary of result values. Default: No results (empty dictionary).
#
#         Returns:
#             schedy.Trial: The instance of the new trial.
#         """
#         partial_trial = Trial(
#                 trial_id=None,
#                 experiment=None,
#                 **kwargs)
#         assert self._db is not None, 'Experiment was not added to a database'
#         url = self._trials_url()
#         map_def = partial_trial._to_map_definition()
#         data = json_dumps(map_def, cls=encoding.SchedyJSONEncoder)
#         response = self._db._authenticated_request('POST', url, data=data)
#         errors._handle_response_errors(response)
#         return _trial_from_response(self, response)
#
#     def next_trial(self):
#         """
#         Returns a new trial to be worked on. This trial will be set in the
#         ``RUNNING`` state. This function handles everything so that two
#         workers never start working on the same trial.
#
#         Returns:
#             schedy.Trial: The instance of the requested trial.
#         """
#         assert self._db is not None, 'Experiment was not added to a database'
#         url = urljoin(self._db._experiment_url(self.name), 'nexttrial/')
#         trial = None
#         # Try obtaining a trial and running it until we manage to get hold of a
#         # trial we can indeed run (concurrent trials to run a trial can cause us to
#         # fail, so try and try again)
#         while trial is None:
#             response = self._db._authenticated_request('GET', url)
#             if response.status_code == requests.codes.no_content:
#                 raise errors.NoTrialError('No trial left for experiment {}.'.format(self.name), None)
#             errors._handle_response_errors(response)
#             trial = _trial_from_response(self, response)
#             try:
#                 trial.try_run()
#             except errors.UnsafeUpdateError:
#                 trial = None
#                 logger.debug('Two workers tried to start working on the same trial, retrying.', exc_info=True)
#         return trial
#
#     def all_trials(self):
#         """
#         Retrieves all the trials belonging to this experiment.
#
#         Returns:
#             iterator of :py:class:`schedy.Trial`: An iterator over all the trials of this experiment.
#         """
#         assert self._db is not None, 'Experiment was not added to a database'
#         url = self._trials_url()
#         return PageObjectsIterator(
#             reqfunc=functools.partial(self._db._authenticated_request, 'GET', url),
#             obj_creation_func=functools.partial(_make_trial, self),
#         )
#
#     def get_trial(self, trial_id):
#         """
#         Retrieves a trial by id.
#
#         Args:
#             trial_id (str): Id of the trial to retrieve.
#
#         Returns:
#             schedy.Trial: Instance of the requested trial.
#         """
#         assert self._db is not None, 'Experiment was not added to a database'
#         url = self._db._trial_url(self.name, trial_id)
#         response = self._db._authenticated_request('GET', url)
#         errors._handle_response_errors(response)
#         trial = _trial_from_response(self, response)
#         return trial
#
#     def __str__(self):
#         try:
#             return '{}(name={!r}, params={})'.format(self.__class__.__name__, self.name, self._get_params())
#         except NotImplementedError:
#             return '{}(name={!r})'.format(self.__class__.__name__, self.name)
#
#     def push_updates(self):
#         """
#         Push all the updates made to this experiment to the service.
#         """
#         assert self._db is not None, 'Experiment was not added to a database'
#         url = self._db._experiment_url(self.name)
#         content = self._to_map_definition()
#         data = json_dumps(content, cls=encoding.SchedyJSONEncoder)
#         response = self._db._authenticated_request('PUT', url, data=data)
#         errors._handle_response_errors(response)
#
#     def delete(self, ensure=True):
#         """
#         Deletes this experiment.
#
#         Args:
#             ensure (bool): If true, an exception will be raised if the experiment was
#                 deleted before this call.
#         """
#         assert self._db is not None, 'Experiment was not added to a database'
#         url = self._db._experiment_url(self.name)
#         if ensure:
#             headers = {'If-Match': '*'}
#         else:
#             headers = dict()
#         response = self._db._authenticated_request('DELETE', url, headers=headers)
#         errors._handle_response_errors(response)
#
#     @classmethod
#     def _create_from_params(cls, name, status, params):
#         raise NotImplementedError()
#
#     def _get_params(self):
#         raise NotImplementedError()
#
#     def _to_map_definition(self):
#         try:
#             scheduler = self._SCHEDULER_NAME
#         except AttributeError as e:
#             raise_from(AttributeError('Experiment implementations should define a _SCHEDULER_NAME attribute'), e)
#         return {
#                 'status': self.status,
#                 'scheduler': {scheduler: self._get_params()},
#             }
#
#     @staticmethod
#     def _from_map_definition(schedulers, map_def):
#         try:
#             name = str(map_def['name'])
#             status = str(map_def['status'])
#             scheduler_def_map = dict(map_def['scheduler'])
#             if len(scheduler_def_map) != 1:
#                 raise ValueError('Invalid scheduler definition: {}.'.format(scheduler_def_map))
#             sched_def_key, sched_def_val = next(iter(scheduler_def_map.items()))
#             scheduler = str(sched_def_key)
#             params = sched_def_val
#         except (ValueError, KeyError) as e:
#             raise_from(ValueError('Invalid map definition for experiment.'), e)
#         if not _check_status(status):
#             raise ValueError('Invalid or unknown status value: {}.'.format(status))
#         try:
#             exp_type = schedulers[scheduler]
#         except KeyError as e:
#             raise ValueError('Invalid or unregistered scheduler name: {}.'.format(scheduler))
#         return exp_type._create_from_params(
#                 name=name,
#                 status=status,
#                 params=params)
#
#     def _trials_url(self):
#         return urljoin(self._db._experiment_url(self.name), 'trials/')
#
# class ManualSearch(Experiment):
#     """
#     Represents a manual search, that is to say an experiment for which the only
#     trials returned by :py:meth:`schedy.Experiment.next_trial` are trials that were
#     queued beforehand (by using :py:meth:`schedy.Experiment.add_trial` for
#     example).
#     """
#     _SCHEDULER_NAME = 'Manual'
#
#     @classmethod
#     def _create_from_params(cls, name, status, params):
#         if params is not None:
#             raise ValueError('Expected no parameters for manual search, found {}.'.format(type(params)))
#         return cls(name=name, status=status)
#
#     def _get_params(self):
#         return None
#
# class RandomSearch(Experiment):
#     _SCHEDULER_NAME = 'RandomSearch'
#
#     def __init__(self, name, distributions, status=Experiment.RUNNING):
#         """
#         Represents a random search, that is to say en experiment that returns
#         trials with random hyperparameters when no trial was queued manually using
#         :py:meth:`schedy.Experiment.add_trial`.
#
#         If you create a trial manually for this experiment, it must have only and
#         all the hyperparameters specified in the ``distributions`` parameter.
#
#         Args:
#             name (str): Name of the experiment. An experiment is uniquely
#                 identified by its name.
#             distributions (dict): A dictionary of distributions (see
#                 :py:mod:`schedy.random`), whose keys are the names of the
#                 hyperparameters.
#             status (str): Status of the experiment. See :ref:`experiment_status`.
#         """
#         super(RandomSearch, self).__init__(name, status)
#         self.distributions = distributions
#
#     @classmethod
#     def _create_from_params(cls, name, status, params):
#         try:
#             items = params.items()
#         except AttributeError as e:
#             raise ValueError('Expected parameters as a dict, found {}.'.format(type(params)))
#         distributions = dict()
#         for key, dist_def in items:
#             try:
#                 dist_name_raw, dist_args = next(iter(dist_def.items()))
#                 dist_name = str(dist_name_raw)
#             except (KeyError, TypeError) as e:
#                 raise_from(ValueError('Invalid distribution definition.'), e)
#             try:
#                 dist_type = _DISTRIBUTION_TYPES[dist_name]
#             except KeyError as e:
#                 raise ValueError('Invalid or unknown distribution type: {}.'.format(dist_name))
#             distributions[key] = dist_type._from_args(dist_args)
#         return cls(name=name, distributions=distributions, status=status)
#
#     def _get_params(self):
#         return {key: {dist._FUNC_NAME: dist._args()} for key, dist in self.distributions.items()}
#
# class PopulationBasedTraining(Experiment):
#     _SCHEDULER_NAME = 'PBT'
#
#     def __init__(self, name, objective, result_name, exploit, explore=dict(), initial_distributions=dict(), population_size=None, status=Experiment.RUNNING, max_generations=None):
#         """
#         Implements Population Based Training (see `paper
#         <https://arxiv.org/pdf/1711.09846.pdf>`_).
#
#         You have two ways to specify the initial trials for Population Based
#         training. You can create them manually using
#         :py:meth:`schedy.Experiment.add_trial`, or you can specify the
#         ``initial_distributions`` and ``population_size`` parameters.
#
#         If you create a trial manually for this experiment, it must have at least
#         the hyperparameters specified in the ``explore`` parameter.
#
#         Args:
#             name (str): Name of the experiment. An experiment is uniquely
#                 identified by its name.
#             objective (str): The objective of the training, either
#                 :py:attr:`schedy.pbt.MINIMIZE` (to
#                 minimize a result) or
#                 :py:attr:`schedy.pbt.MAXIMIZE` (to
#                 maximize a result).
#             result_name (str): The name of the result to optimize. This result
#                 must be present in the results of all
#                 :py:attr:`~schedy.Experiment.RUNNING` trials of this experiment.
#             exploit (schedy.pbt.ExploitStrategy): Strategy to use to
#                 exploit the results (i.e. to focus on the most promising trials).
#             explore (dict): Strategy to use to explore new hyperparameter values.
#                 The keys of the dictionary are the name of the
#                 hyperparameters (str), and the values are the strategy
#                 associated with the hyperparameter
#                 (:py:class:`schedy.pbt.ExploreStrategy`). Values for the
#                 omitted hyperparameters will not be explored. This parameter is
#                 optional: if you do not specify any explore strategy, only
#                 exploitation will be used.
#             initial_distributions (dict): The initial distributions for the
#                 hyperparameters, as dictionary of distributions (see
#                 :py:mod:`schedy.random`) whose keys are the names of the
#                 hyperparameters. This parameter optional, you can also create
#                 the initial trials manually. If you use this parameter, make sure
#                 to use ``population_size`` as well.
#             population_size (int): Number of initial trials to create, before
#                 starting to exploit/explore (i.e. size of the population). It
#                 does **not** have to be the number of trials you can process in
#                 parallel. The original paper used values between 10 and 80.
#             status (str): Status of the experiment. See :ref:`experiment_status`.
#             max_generations (int): Maximum number of generations to run before
#                 marking the experiment the experiments as done
#                 (:py:ref:`experiment_status`). When the maximum number of
#                 generations is reached, subsequent calls to
#                 :py:meth:`schedy.Experiment.next_trial` will raise
#                 :py:class:`schedy.errors.NoTrialError`, to indicate that the trial
#                 queue is empty.
#         """
#         super(PopulationBasedTraining, self).__init__(name, status)
#         self.objective = objective
#         self.result_name = result_name
#         self.exploit = exploit
#         self.explore = explore
#         self.initial_distributions = initial_distributions
#         self.population_size = population_size
#         self.max_generations = max_generations
#
#     @classmethod
#     def _create_from_params(cls, name, status, params):
#         kwargs = {
#             'name': name,
#             'status': status,
#             'objective': params['objective'],
#             'result_name': params['qualityResultName'],
#         }
#         exploit_type, exploit_params = next(iter(params['exploit'].items()))
#         kwargs['exploit'] = _EXPLOIT_STRATEGIES[exploit_type]._from_params(exploit_params)
#         population_size = params.get('numParallel')
#         if population_size is not None:
#             kwargs['population_size'] = population_size
#         initial_distributions = params.get('init')
#         if initial_distributions is not None:
#             init_param = dict()
#             for hp, dist_map in initial_distributions.items():
#                 dist_name, dist_params = next(iter(dist_map.items()))
#                 init_param[hp] = _DISTRIBUTION_TYPES[dist_name]._from_args(dist_params)
#             kwargs['initial_distributions'] = init_param
#         explore = params.get('explore')
#         if explore is not None:
#             explore_map = dict()
#             for hp, strat_map in explore.items():
#                 strat_name, strat_params = next(iter(strat_map.items()))
#                 explore_map[hp] = _EXPLORE_STRATEGIES[strat_name]._from_params(strat_params)
#             kwargs['explore'] = explore_map
#         max_generations = params.get('max_generations')
#         if max_generations is not None:
#             kwargs['max_generations'] = max_generations
#         return cls(**kwargs)
#
#     def _get_params(self):
#         params = {
#             'objective': self.objective,
#             'qualityResultName': self.result_name,
#         }
#         if self.population_size:
#             params['numParallel'] = self.population_size
#         if self.initial_distributions:
#             params['init'] = {
#                 name: {dist._FUNC_NAME: dist._args()} for name, dist in self.initial_distributions.items()
#             }
#         params['exploit'] = {self.exploit._EXPLOIT_STRATEGY_NAME: self.exploit._get_params()}
#         if self.explore:
#             params['explore'] = {
#                 name: {strat._EXPLORE_STRATEGY_NAME: strat._get_params()} for name, strat in self.explore.items()
#             }
#         if self.max_generations:
#             params['maxGenerations'] = self.max_generations
#         return params
#
# def _make_experiment(db, data):
#     try:
#         exp_data = dict(data)
#     except ValueError as e:
#         raise_from(errors.UnhandledResponseError('Expected experiment data as a dict, received {}.'.format(type(data)), None), e)
#     try:
#         exp = Experiment._from_map_definition(db._schedulers, exp_data)
#     except ValueError as e:
#         raise_from(errors.UnhandledResponseError('Response contains an invalid experiment', None), e)
#     exp._db = db
#     return exp
#
