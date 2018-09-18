# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import datetime
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
from .projects import Projects
from .jwt import JWTTokenAuth

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
        self.project = lambda project_id: urljoin(self.root, '/projects/{}/'.format(urlquote(project_id)))
        self.project_permissions = urljoin(self.root, '/projects/{projectID}/permissions/')
        self.project_permissions_edit = urljoin(self.root, '/projects/{projectID}/permissions/{permissionEmail}/')

        # Experiments management
        self.experiments = lambda project_id: urljoin(self.root, '/projects/{}/experiments/'.format(urlquote(project_id)))
        self.experiment = lambda project_id, exp_name: urljoin(self.root, '/projects/{}/experiments/{}/'.format(urlquote(project_id), urlquote(exp_name)))
        self.schedule = lambda project_id, exp_name: urljoin(self.root, '/projects/{}/experiments/{}/schedule'.format(urlquote(project_id), urlquote(exp_name)))
        self.schedulers = lambda project_id, exp_name: urljoin(self.root, '/projects/{}/experiments/{}/schedulers'.format(urlquote(project_id), urlquote(exp_name)))

        # Trials management
        self.trials = lambda project_id, exp_name: urljoin(self.root, '/projects/{}/experiments/{}/trials/'.format(urlquote(project_id), urlquote(exp_name)))
        self.trial = lambda project_id, exp_name, trial_id: urljoin(self.root, '/projects/{}/experiments/{}/trials/{}/'.format(urlquote(project_id), urlquote(exp_name), urlquote(trial_id)))


class Config(object):

    _default_config_path = os.path.join(os.path.expanduser('~'), '.schedy', 'client.json')

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

        self._schedulers = dict()
        # self._register_default_schedulers()
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
        assert self.config.token_type in ['apiToken', 'password']

        response = self._perform_request('POST', self.routes.signin,
                                         json={'email': self.config.email, 'token': self.config.api_token, 'type': self.config.token_type},
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
        """
        Registers a new type of experiment. You should never have to use this
        function yourself.

        Args:
            experiment_type (class): Type of the experiment, it must have an
                attribute called _SCHEDULER_NAME.
        """
        self._schedulers[experiment_type._SCHEDULER_NAME] = experiment_type

#     def _register_default_schedulers(self):
#         self._register_scheduler(RandomSearch)
#         self._register_scheduler(ManualSearch)
#         self._register_scheduler(PopulationBasedTraining)
# 
#     def _all_experiments_url(self):
#         return urljoin(self.root, 'experiments/')
# 
#     def _experiment_url(self, name):
#         return urljoin(self._all_experiments_url(), '{}/'.format(urlquote(name, safe='')))
# 
#     def _trial_url(self, experiment, trial):
#         return urljoin(self.root, 'experiments/{}/trials/{}/'.format(urlquote(experiment, safe=''), urlquote(trial, safe='')))

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


class Client(object):

    def __init__(self, config_path=None, config_override=None):
        """
           Client is the central component of Schedy. It represents your
           connection the the Schedy service.

           Args:
               config_path (str or file-object): Path to the client configuration file. This file
                   contains your credentials (email, API token). By default,
                   ~/.schedy/client.json is used. See :ref:`setup` for
                   instructions about how to use this file.
               config_override (dict): Content of the configuration. You can use this to
                   if you do not want to use a configuration file.
        """
        self.config = Config(config_path, config_override)
        self.core = Core(self.config)

        self.projects = Projects(self.core)

    def create_project(self, project_id, project_name):
        return self.projects.create(project_id, project_name)

    def get_project(self, project_id):
        return self.projects.get(project_id)

    def get_projects(self):
        return self.projects.get_all()

    def disable_project(self, project_id):
        return self.projects.disable(project_id)
