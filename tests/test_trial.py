# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

from unittest import TestCase
from schedy import Core, Config, Trial
import responses
from schedy.core import JWTTokenAuth
from datetime import datetime


class TestTrial(TestCase):
    def setUp(self):
        self.email = 'test@schedy.io'
        self.token = 'TOKEN'
        self.project_id = 'test-12345'
        self.project_name = 'Test 12345'
        self.exp_name = 'Experiment name'
        self.root = 'http://fake.schedy.io/'
        self.auth_request = {'email': self.email, 'token': self.token, 'type': 'apiToken', 'root': self.root}
        self.config = dict(self.auth_request)
        self.config['root'] = self.root
        self.trial_id = '0.23975875348'
        self.etag = '33a64df551425fcc55e4d42a148795d9f25f89d4'
        self.status = 'QUEUED'
        self.hp = {'hp0': 0.3, 'hp1': 23}
        self.metrics = {'acc': 0.99}
        self.metadata = {'final_run': True}

        self.core = Core(Config(config_path=None, config=self.config))
        self.trial = Trial(self.core, self.project_id, self.exp_name, self.trial_id,
                           self.status, hyperparameters=self.hp, metrics=self.metrics, metadata=self.metadata)
        self.core._jwt_token = JWTTokenAuth('TEST JWT TOKEN', datetime(3018, 1, 1))
        self.trial.etag = self.etag

    @responses.activate
    def test_update(self):

        responses.add(
            responses.PUT,
            self.core.routes.trial(self.project_id, self.exp_name, self.trial_id),
            json={},
        )

        self.trial.hyperparameters = {'hp0': 0.5, 'hp1': 0}
        self.trial.status = Trial.CRASHED
        self.trial.etag = self.etag
        self.trial.update(safe=False)

        expected_trial = Trial(self.core, self.project_id, self.exp_name, self.trial_id,
                               'CRASHED',
                               hyperparameters={'hp0': 0.5, 'hp1': 0},
                               metrics=self.metrics,
                               metadata=self.metadata,
                               etag=self.etag)

        self.assertEqual(expected_trial, self.trial)

    @responses.activate
    def test_try_run(self):
        responses.add(
            responses.PUT,
            self.core.routes.trial(self.project_id, self.exp_name, self.trial_id),
            json={},
        )

        self.assertEqual('QUEUED', self.trial.status)
        self.trial.try_run()
        self.assertEqual('RUNNING', self.trial.status)

    @responses.activate
    def test_delete(self):
        responses.add(
            responses.DELETE,
            self.core.routes.trial(self.project_id, self.exp_name, self.trial_id),
            json={},
        )

        self.trial.delete()

        self.assertEqual(responses.DELETE, responses.calls[0].request.method)

    def test__from_description(self):
        expected_trial = Trial(self.core, self.project_id, self.exp_name, self.trial_id, self.status, self.hp, {'acc': 0.99}, {'final_run': True}, etag=self.etag)
        self.assertEqual(expected_trial, self.trial)
