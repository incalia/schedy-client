# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import datetime
import functools
import json
import logging
import os.path

import requests
from requests.adapters import HTTPAdapter
from requests.compat import urljoin, quote as urlquote
from requests.packages.urllib3.util.retry import Retry
from six import raise_from

from . import errors, encoding
from .compat import json_dumps
from .experiments import RandomSearch, ManualSearch, PopulationBasedTraining
from .jwt import JWTTokenAuth
from .pagination import PageObjectsIterator

logger = logging.getLogger(__name__)


class SchedyRetry(Retry):
    BACKOFF_MAX = 8 * 60

    def increment(self, method=None, url=None, response=None, error=None, *args, **kwargs):
        logger.warning('Error while querying Schedy service, retrying.')
        if response is not None:
            logger.warning('Server message: {!s}'.format(response.data))
        return super(SchedyRetry, self).increment(
            method=method,
            url=url,
            response=response,
            error=error,
            *args,
            **kwargs)


#: Number of retries if the authentication fails
NUM_AUTH_RETRIES = 2


class _Routes(object):

    def __init__(self, root):
        self.root = root

        # Accounts management
        self.signup = urljoin(self.root, '/accounts/signup/')
        self.signin = urljoin(self.root, '/accounts/signin/')
        self.generate_token = urljoin(self.root, '/accounts/generateToken/')
        self.activate = urljoin(self.root, '/accounts/activate/')
        self.disable = urljoin(self.root, '/accounts/disable/')

        # Project Management
        self.projects = urljoin(self.root, '/projects/')
        self.project = lambda project_id: urljoin(self.root, '/projects/{}/'.format(project_id))
        self.project_permissions = urljoin(self.root, '/projects/{projectID}/permissions/')
        self.project_permissions_edit = urljoin(self.root, '/projects/{projectID}/permissions/{permissionEmail}/')

        # Experiments management
        self.experiments = lambda project_id: urljoin(self.root, '/projects/{}/experiments/'.format(project_id))
        self.experiment = lambda project_id, exp_name: urljoin(self.root, '/projects/{}/experiments/{}/'.format(project_id, exp_name))
        self.schedule = lambda project_id, exp_name: urljoin(self.root, '/projects/{}/experiments/{}/schedule'.format(project_id, exp_name))
        self.schedulers = lambda project_id, exp_name: urljoin(self.root, '/projects/{}/experiments/{}/schedulers'.format(project_id, exp_name))

        # Trials management
        self.trials = lambda project_id, exp_name: urljoin(self.root, '/projects/{}/experiments/{}/trials/'.format(project_id, exp_name))
        self.trial = lambda project_id, exp_name, trial_id: urljoin(self.root, '/projects/{}/experiments/{}/trials/{}/'.format(project_id, exp_name, trial_id))


class Config(object):

    @classmethod
    @property
    def _default_config_path(cls):
        return os.path.join(os.path.expanduser('~'), '.schedy', 'client.json')

    def __init__(self, config_path, config):
        if config is None:
            if config_path is None:
                config_path = Config._default_config_path
            if hasattr(config_path, 'read'):
                config = json.loads(config_path.read())
            else:
                with open(config_path) as f:
                    config = json.load(f)

        self.root = urljoin(config['root'], '/')
        self.email = config['email']
        self.token_type = config.get('token_type', 'apiToken')

        allowed_token_types = ['apiToken', 'password']
        if self.token_type not in allowed_token_types:
            raise ValueError('Configuration value token_type must be one of {}.'.format(', '.join(allowed_token_types)))
        self.api_token = config['token']


class Core(object):

    def __init__(self, config):

        self.config = config
        self._email = config.email
        self._token_type = config.token_type
        self._api_token = config.api_token

        self._schedulers = dict()
        self._register_default_schedulers()
        self._jwt_token = None
        self._session = None

    @property
    def routes(self):
        return _Routes(self.config.root)

    def _authenticate(self):
        """
        Renew authentication. You do not usually need to call this function, as
        it will always be called automatically when needed.
        """

        logger.debug('Renewing authentication')
        assert self._token_type in ['apiToken', 'password']

        response = self._perform_request('POST', self.routes.signin,
                                         json={'email': self._email, 'token': self._api_token, 'type': self._token_type},
                                         headers={'Content-Type': 'application/json'}
                                         )
        errors._handle_response_errors(response)
        try:
            token_data = response.json()
        except ValueError as e:
            raise_from(errors.ServerError('Response contains invalid JSON:\n' + response.text, None), e)
        try:
            jwt_token = token_data['token']
            expires_at = datetime.datetime.fromtimestamp(token_data['expiresAt'])
        except (KeyError, OverflowError, OSError) as e:
            raise_from(errors.ServerError('Response contains invalid token data.', None), e)
        self._jwt_token = JWTTokenAuth(jwt_token, expires_at)
        logger.debug('A new token was obtained.')

    def _register_scheduler(self, experiment_type):
        '''
        Registers a new type of experiment. You should never have to use this
        function yourself.

        Args:
            experiment_type (class): Type of the experiment, it must have an
                attribute called _SCHEDULER_NAME.
        '''
        self._schedulers[experiment_type._SCHEDULER_NAME] = experiment_type

    def _register_default_schedulers(self):
        self._register_scheduler(RandomSearch)
        self._register_scheduler(ManualSearch)
        self._register_scheduler(PopulationBasedTraining)

    def _all_experiments_url(self):
        return urljoin(self.root, 'experiments/')

    def _experiment_url(self, name):
        return urljoin(self._all_experiments_url(), '{}/'.format(urlquote(name, safe='')))

    def _job_url(self, experiment, job):
        return urljoin(self.root, 'experiments/{}/jobs/{}/'.format(urlquote(experiment, safe=''), urlquote(job, safe='')))

    def authenticated_request(self, *args, **kwargs):
        response = None
        for _ in range(NUM_AUTH_RETRIES):
            if self._jwt_token is None or self._jwt_token.expires_soon():
                self._authenticate()
            response = self._perform_request(*args, auth=self._jwt_token, **kwargs)
            if response.status_code != requests.codes.unauthorized:
                break
        return response

    def _make_session(self):
        self._session = requests.Session()
        retry_mgr = SchedyRetry(
                total=10,
                read=10,
                connect=10,
                backoff_factor=0.4,
                status_forcelist=frozenset((requests.codes.server_error, requests.codes.unavailable)),
                # Careful: POST and PATCH are in the whitelist. This means that
                # the server should not be in an incomplete state or POSTING
                # and PATCHING twice could do weird things. We do this because
                # we do not want Schedy to crash in the face of the user when
                # there's a connection or benign error.
                method_whitelist=frozenset(('HEAD', 'TRACE', 'GET', 'PUT', 'OPTIONS', 'DELETE', 'POST', 'PATCH')),
            )
        adapter = HTTPAdapter(max_retries=retry_mgr)
        self._session.mount('http://', adapter)
        self._session.mount('https://', adapter)

    def _perform_request(self, *args, **kwargs):
        if self._session is None:
            self._make_session()
        if 'data' in kwargs:
            logger.debug('Sent headers: %s', kwargs.get('headers'))
            logger.debug('Sent data: %s', kwargs['data'])
        req = self._session.request(*args, **kwargs)
        logger.debug('Received headers: %s', req.headers)
        logger.debug('Received data: %s', req.text)
        return req


class Account(object):
    def __init__(self, core):
        self.core = core


class SchedyDef(object):
    def __init__(self, d):
        self.d = d

    def to_json(self):
       return json_dumps(self.d, cls=encoding.SchedyJSONEncoder)


class Trial(object):

    def __init__(self, project_id=None, experiment_id=None, trial_id=None, hyperparameters=None, metrics=None,
                 status=None, metadata=None):

        self.hyperparameters = hyperparameters
        self.metadata = metadata
        self.metrics = metrics
        self.status = status
        self.project_id = project_id
        self.experiment_id = experiment_id
        self.trial_id = trial_id

        self.trial_data = {}
        if self.hyperparameters:
            self.trial_data['hyperparameters'] = self.hyperparameters
        if self.metadata:
            self.trial_data['metadata'] = self.metadata
        if self.metrics:
            self.trial_data['metrics'] = self.metrics

    def _map(self, param_value):
        TYPES_MAP = {
            type(None): 'n',
            float: 'f',
            int: 'i',
            str: 's',
            bool: 'b',
            bytes: 'd',
            dict: 'm',
            list: 'a',
        }

        if isinstance(param_value, (type(None), float, int, str, bool, bytes)):
            v = param_value
            if param_value == float('inf'):
                v = '+Inf'
            elif param_value == float('-inf'):
                v = '-Inf'
            elif param_value == float('nan'):
                v = 'NaN'
            if type(param_value) is bytes:
                v = base64.b64encode(param_value).decode('utf-8')
            return {TYPES_MAP[type(param_value)]: v}
        elif isinstance(param_value, list):
            return {TYPES_MAP[type(param_value)]: [self._map(x) for x in param_value]}
        elif isinstance(param_value, dict):
            return {TYPES_MAP[type(param_value)]: {k: self._map(v) for k, v in param_value.items()}}
        else:
            raise ValueError(
                '{} do not support objects with type {}'.format(self.__class__.__name__, type(param_value)))

    def to_def(self):

        _def = {}

        for k1, v1 in self.trial_data.items():
            if v1 is not None:
                _def[k1] = {}
                print(v1)
                for k2, v2 in v1.items():
                    _def[k1][k2] = self._map(v2)

        _def['status'] = self.status
        return SchedyDef(_def)

    @classmethod
    def _imap(self, param):

        # TYPES_MAP = {
        #     'n': type(None),
        #     'f': float,
        #     'i': int,
        #     's': str,
        #     'b': bool,
        #     'd': bytes,
        #     'm': dict,
        #     'a': list,
        # }

        for k, v in param.items():

            if k == 'f' and v in ['-Inf', '+Inf', 'NaN']:
                return float(v)

            # if type(v) != TYPES_MAP[k]:
            #     raise ValueError('Invalid trial json ({} != {})'.format(type(v), TYPES_MAP[k]))

            if k in 'nfisb':  # NoneType, float, int, bool
                return v
            elif k == 'd':  # bytes
                return base64.b64decode(v.encode('utf-8'))
            elif k == 'm':  # dict
                return {dk: Trial._imap(dv) for dk, dv in v.items()}
            elif k == 'a':  # list
                return [Trial._imap(x) for x in v]

    @classmethod
    def from_def(cls, definition):

        project_id = definition.get('project')
        experiment_id = definition.get('experiment')
        trial_id = definition.get('id')
        metrics = definition.get('metrics')
        status = definition.get('status')

        hyperparameters = definition.get('hyperparameters') or dict()
        for k, v in hyperparameters.items():
            hyperparameters[k] = Trial._imap(v)

        metadata = definition.get('metadata') or dict()
        for k, v in metadata.items():
            metadata[k] = Trial._imap(v)

        return cls(project_id, experiment_id, trial_id, hyperparameters, metrics, status, metadata)


class Trials(object):
    def __init__(self, core):
        self.core = core


class Experiment(object):
    def __init__(self, core, project_id, name, params, metrics):
        assert params is None or isinstance(params, list)
        assert metrics is None or isinstance(metrics, list)

        self.core = core
        self.name = name
        self.trials = Trials(self.core)
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
        url = self.core.routes.trial(self.project_id, self.name, trial_id)
        trial = Trial(self.project_id, self.name, trial_id, hyperparameters, metrics, status, metadata)
        response = self.core.authenticated_request('PATCH', url, data=trial.to_def().to_json())

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
        '''
            Retrieves an experiment from the Schedy service by name.

            Args:
                name (str): Name of the experiment.

            Returns:
                schedy.Experiment: An experiment of the appropriate type.

        '''
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
        '''
        Retrieves all the experiments from the Schedy service.

        Returns:
            iterator of :py:class:`schedy.Experiment`: Iterator over all the experiments.
        '''
        return PageObjectsIterator(
            reqfunc=functools.partial(self.core.authenticated_request, 'GET', self.core.routes.experiments(self.project_id)),
            obj_creation_func=functools.partial(Experiment.from_def, self.core),
            expected_field='experiments'
        )


class Project(object):

    def __init__(self, core, desc):
        self.core = core
        self.desc = desc
        self.id = desc['id']
        self.experiments = Experiments(self.core, self.id)

    def to_def(self):
        return self.desc

    def add_experiment(self, name, params=None, metrics=None):
        '''
        Adds an experiment to the Schedy service. Use this function to create
        new experiments.

        Args:
            exp (schedy.Experiment): The experiment to add.

        '''

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
            "projectID": project_id,
            "name": project_name
        }

        data = json_dumps(content, cls=encoding.SchedyJSONEncoder)
        response = self.core.authenticated_request('POST', url, data=data)
        # Handle code 412: Precondition failed

        if response.status_code == requests.codes.precondition_failed:
            raise errors.ResourceExistsError(response.text + '\n' + url, response.status_code)
        else:
            errors._handle_response_errors(response)

    def describe(self, project_id):
        assert len(project_id) > 0, "project_id should be a nonempty string"

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


class Client(object):

    def __init__(self, config_path=None, config_override=None):
        '''
           Client is the central component of Schedy. It represents your
           connection the the Schedy service.

           Args:
               config_path (str or file-object): Path to the client configuration file. This file
                   contains your credentials (email, API token). By default,
                   ~/.schedy/client.json is used. See :ref:`setup` for
                   instructions about how to use this file.
               config_override (dict): Content of the configuration. You can use this to
                   if you do not want to use a configuration file.
        '''
        self.config = Config(config_path, config_override)
        self.core = Core(self.config)

        self.account = Account(self.core)
        self.projects = Projects(self.core)

    def create_project(self, project_id, project_name):
        return self.projects.create(project_id, project_name)

    def get_project(self, project_id):
        return self.projects.get(project_id)

    def get_projects(self):
        return self.projects.get_all()

    def disable_project(self, project_id):
        return self.projects.disable(project_id)