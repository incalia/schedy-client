# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import json
import logging
import os.path

import requests
from requests.adapters import HTTPAdapter
from requests.compat import urljoin
from requests.packages.urllib3.util.retry import Retry
from six import raise_from

from . import errors
from .compat import uurlquote
from .jwt import JWTTokenAuth

logger = logging.getLogger(__name__)


class _Retry(Retry):
    BACKOFF_MAX = 8 * 60

    def increment(self, method=None, url=None, response=None, error=None, *args, **kwargs):
        logger.warning('Error while querying Schedy service, retrying.')
        if response is not None:
            logger.warning('Server message: {!s}'.format(response.data))
        return super(_Retry, self).increment(
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
        self._root = root

        # Accounts management
        self.signup = urljoin(self.root, '/accounts/signup/')
        self.signin = urljoin(self.root, '/accounts/signin/')
        self.generate_token = urljoin(self.root, '/accounts/generateToken/')
        self.activate = urljoin(self.root, '/accounts/activate/')
        self.disable = urljoin(self.root, '/accounts/disable/')

        self.projects = urljoin(self.root, '/projects/')
        self.project = lambda project_id: urljoin(self.root, '/projects/{}/'.format(uurlquote(project_id)))
        self.project_permissions = lambda project_id: urljoin(self.root, '/projects/{}/permissions/'.format(uurlquote(project_id)))
        self.project_permissions_edit = lambda project_id, email_address: urljoin(self.root, '/projects/{}/permissions/{}/'.format(uurlquote(project_id), uurlquote(email_address)))

        # Experiments management
        self.experiments = lambda project_id: urljoin(self.root, '/projects/{}/experiments/'.format(uurlquote(project_id)))
        self.experiment = lambda project_id, exp_name: urljoin(self.root, '/projects/{}/experiments/{}/'.format(uurlquote(project_id), uurlquote(exp_name)))
        self.schedule = lambda project_id, exp_name: urljoin(self.root, '/projects/{}/experiments/{}/schedule'.format(uurlquote(project_id), uurlquote(exp_name)))
        self.schedulers = lambda project_id, exp_name: urljoin(self.root, '/projects/{}/experiments/{}/schedulers'.format(uurlquote(project_id), uurlquote(exp_name)))

        # Trials management
        self.trials = lambda project_id, exp_name: urljoin(self.root, '/projects/{}/experiments/{}/trials/'.format(uurlquote(project_id), uurlquote(exp_name)))
        self.trial = lambda project_id, exp_name, trial_id: urljoin(self.root, '/projects/{}/experiments/{}/trials/{}/'.format(uurlquote(project_id), uurlquote(exp_name), uurlquote(trial_id)))

    @property
    def root(self):
        return self._root

    @root.setter
    def root(self, value):
        raise AttributeError("Cannot set `root` attribute")


class Config(object):

    _default_config_path = os.path.join(os.path.expanduser('~'), '.schedy', 'client.json')

    def __init__(self, config_path=None, config=None):
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

        assert isinstance(config, Config)

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
        retry_mgr = _Retry(
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


class DataEqMixin(object):
    def __eq__(self, other):
        return self is other or (isinstance(other, type(self)) and vars(self) == vars(other))

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(tuple(sorted(vars(self).items())))

    def __repr__(self):
        return type(self).__name__ + '{\n' + '\n  '.join(
            '{}: {!r}'.format(key, value) for key, value in sorted(vars(self).items())) + '\n}'

