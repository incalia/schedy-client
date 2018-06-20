# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from six import raise_from

from .experiments import Experiment, RandomSearch, ManualSearch, PopulationBasedTraining, _make_experiment
from .jwt import JWTTokenAuth
from .pagination import PageObjectsIterator
from . import errors, encoding
from .compat import json_dumps

import functools
import json
import requests
import os.path
import datetime
from requests.compat import urljoin, quote as urlquote
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import logging

logger = logging.getLogger(__name__)

class SchedyRetry(Retry):
    BACKOFF_MAX = 8 * 60

    def increment(self, method=None, url=None, response=None, error=None, *args, **kwargs):
        logger.warn('Error while querying Schedy service, retrying.')
        if response is not None:
            logger.warn('Server message: {!s}'.format(response.data))
        return super(SchedyRetry, self).increment(
            method=method,
            url=url,
            response=response,
            error=error,
            *args,
            **kwargs)

#: Number of retries if the authentication fails.
NUM_AUTH_RETRIES = 2

def _default_config_path():
    return os.path.join(os.path.expanduser('~'), '.schedy', 'client.json')

class SchedyDB(object):
    def __init__(self, config_path=None, config_override=None):
        '''
        SchedyDB is the central component of Schedy. It represents your
        connection the the Schedy service.

        Args:
            config_path (str or file-object): Path to the client configuration file. This file
                contains your credentials (email, API token). By default,
                ~/.schedy/client.json is used. See :ref:`setup` for
                instructions about how to use this file.
            config_override (dict): Content of the configuration. You can use this to
                if you do not want to use a configuration file.
        '''
        self._load_config(config_path, config_override)
        # Add the trailing slash if it's not there
        if len(self.root) == 0 or self.root[-1] != '/':
            self.root = self.root + '/'
        self._schedulers = dict()
        self._register_default_schedulers()
        self._jwt_token = None
        self._jwt_expiration = datetime.datetime(year=1970, month=1, day=1)
        self._session = None

    def _authenticate(self):
        '''
        Renew authentication. You do not usually need to call this function, as
        it will always be called automatically when needed.
        '''
        logger.debug('Renewing authentication')
        if self.token_type == 'password':
            url = urljoin(self.root, 'passauth/')
        else:
            url = urljoin(self.root, 'token/')
        response = self._perform_request('POST', url, json={'email': self.email, 'token': self.api_token})
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

    def add_experiment(self, exp):
        '''
        Adds an experiment to the Schedy service. Use this function to create
        new experiments.

        Args:
            exp (schedy.Experiment): The experiment to add.

        Example:
            >>> db = schedy.SchedyDB()
            >>> exp = schedy.ManualSearch('TestExperiment')
            >>> db.add_experiment(exp)
        '''
        url = self._experiment_url(exp.name)
        content = exp._to_map_definition()
        data = json_dumps(content, cls=encoding.SchedyJSONEncoder)
        response = self._authenticated_request('PUT', url, data=data, headers={'If-None-Match': '*'})
        # Handle code 412: Precondition failed
        if response.status_code == requests.codes.precondition_failed:
            raise errors.ResourceExistsError(response.text, response.status_code)
        else:
            errors._handle_response_errors(response)
        exp._db = self

    def get_experiment(self, name):
        '''
        Retrieves an experiment from the Schedy service by name.

        Args:
            name (str): Name of the experiment.

        Returns:
            schedy.Experiment: An experiment of the appropriate type.
        
        Example:
            >>> db = schedy.SchedyDB()
            >>> exp = db.get_experiment('TestExperiment')
            >>> print(type(exp))
            <class 'schedy.experiments.ManualSearch'>
        '''
        url = self._experiment_url(name)
        response = self._authenticated_request('GET', url)
        errors._handle_response_errors(response)
        try:
            content = dict(response.json())
        except ValueError as e:
            raise_from(errors.ServerError('Response contains invalid JSON dict:\n' + response.text, None), e)
        try:
            exp = Experiment._from_map_definition(self._schedulers, content)
        except ValueError as e:
            raise_from(errors.ServerError('Response contains an invalid experiment', None), e)
        exp._db = self
        return exp

    def get_experiments(self):
        '''
        Retrieves all the experiments from the Schedy service.

        Returns:
            iterator of :py:class:`schedy.Experiment`: Iterator over all the experiments.
        '''
        return PageObjectsIterator(
            reqfunc=functools.partial(self._authenticated_request, 'GET', self._all_experiments_url()),
            obj_creation_func=functools.partial(_make_experiment, self),
        )

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

    def _load_config(self, config_path, config):
        if config is None:
            if config_path is None:
                config_path = _default_config_path()
            if hasattr(config_path, 'read'):
                config = json.loads(config_path.read())
            else:
                with open(config_path) as f:
                    config = json.load(f)
        self.root = config['root']
        self.email = config['email']
        self.token_type = config.get('token_type', 'api_token')
        allowed_token_types = ['api_token', 'password']
        if self.token_type not in allowed_token_types:
            raise ValueError('Configuration value token_type must be one of {}.'.format(', '.join(allowed_token_types)))
        self.api_token = config['token']

    def _authenticated_request(self, *args, **kwargs):
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

