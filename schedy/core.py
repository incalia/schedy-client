# -*- coding: utf-8 -*-

from .experiments import Experiment, RandomSearch, ManualSearch, _make_experiment
from .jwt import JWTTokenAuth
from .pagination import PageObjectsIterator
from . import errors

import functools
import json
import requests
import os.path
import datetime
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
Retry.BACKOFF_MAX = 8 * 60
import logging

logger = logging.getLogger(__name__)

NUM_AUTH_RETRIES = 2

def _default_config_path():
    return os.path.join(os.path.expanduser('~'), '.schedy', 'client.json')

class SchedyDB(object):
    def __init__(self, config_path=None):
        self._load_config(config_path)
        # Add the trailing slash if it's not there
        if len(self.root) == 0 or self.root[-1] != '/':
            self.root = self.root + '/'
        self._schedulers = dict()
        self._register_default_schedulers()
        self._jwt_token = None
        self._jwt_expiration = datetime.datetime(year=1970, month=1, day=1)
        self._session = None

    def authenticate(self):
        logger.debug('Renewing authentication')
        url = urljoin(self.root, 'token/')
        response = self._perform_request('POST', url, json={'email': self.email, 'token': self.api_token})
        errors._handle_response_errors(response)
        try:
            token_data = response.json()
        except ValueError as e:
            raise errors.ServerError('Response contains invalid JSON:\n' + response.text, None) from e
        try:
            jwt_token = token_data['token']
            expires_at = datetime.datetime.fromtimestamp(token_data['expiresAt'])
        except (KeyError, OverflowError, OSError) as e:
            raise errors.ServerError('Response contains invalid token data.', None) from e
        self._jwt_token = JWTTokenAuth(jwt_token, expires_at)
        logger.debug('A new token was obtained.')

    def add_experiment(self, exp):
        url = self._experiment_url(exp.name)
        content = exp._to_map_definition()
        data = json.dumps(content)
        response = self._authenticated_request('PUT', url, data=data, headers={'If-None-Match': '*'})
        # Handle code 412: Precondition failed
        if response.status_code == requests.codes.precondition_failed:
            raise errors.ResourceExistsError(response.text, response.status_code)
        else:
            errors._handle_response_errors(response)
        exp._db = self

    def get_experiment(self, name):
        url = self._experiment_url(name)
        response = self._authenticated_request('GET', url)
        errors._handle_response_errors(response)
        try:
            content = dict(response.json())
        except ValueError as e:
            raise errors.ServerError('Response contains invalid JSON dict:\n' + response.text, None) from e
        try:
            exp = Experiment._from_map_definition(self._schedulers, content)
        except ValueError as e:
            raise errors.ServerError('Response contains an invalid experiment', None) from e
        exp._db = self
        return exp

    def get_experiments(self):
        return PageObjectsIterator(
            reqfunc=functools.partial(self._authenticated_request, 'GET', self._all_experiments_url()),
            obj_creation_func=functools.partial(_make_experiment, self),
        )

    def register_scheduler(self, experiment_type):
        self._schedulers[experiment_type.SCHEDULER_NAME] = experiment_type

    def _register_default_schedulers(self):
        self.register_scheduler(RandomSearch)
        self.register_scheduler(ManualSearch)

    def _all_experiments_url(self):
        return urljoin(self.root, 'experiments/')

    def _experiment_url(self, name):
        return urljoin(self._all_experiments_url(), '{}/'.format(name))

    def _job_url(self, experiment, job):
        return urljoin(self.root, 'experiments/{}/jobs/{}/'.format(experiment, job))

    def _load_config(self, config_path):
        if config_path is None:
            config_path = _default_config_path()
        with open(config_path) as f:
            config = json.load(f)
        self.root = config.get('root', 'https://schedy.io/api/')
        self.email = config['email']
        self.api_token = config['token']

    def _authenticated_request(self, *args, **kwargs):
        response = None
        for _ in range(NUM_AUTH_RETRIES):
            if self._jwt_token is None or self._jwt_token.expires_soon():
                self.authenticate()
            response = self._perform_request(*args, auth=self._jwt_token, **kwargs)
            if response.status_code != requests.codes.unauthorized:
                break
        return response

    def _make_session(self):
        self._session = requests.Session()
        retry_mgr = Retry(
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

