# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

from unittest import TestCase
import schedy
import responses
import requests
from requests.compat import urlparse
import json

from .utils import signin_helper


class TestExperiment(TestCase):
    def setUp(self):
        self.experiment = schedy.Experiment(
            schedy.core.Core(schedy.core.Config(
                config={
                    'root': 'http://fake.schedy.io/',
                    'email': 'test@schedy.io',
                    'token': 'testToken',
                },
            )),
            'test-project',
            'Test experiment',
            hyperparameters=['hp0', 'hp1', 'hp2'],
            metrics=['m0', 'm1', 'm2'],
        )
        signin_helper(self.experiment._core.routes)

    @responses.activate
    def test_create_trial(self):
        responses.add(
            responses.POST,
            self.experiment._core.routes.trials('test-project', 'Test experiment'),
            status=requests.codes.ok,
            body='{"id": ".12345"}',
            headers={'ETag': '456'},
        )
        trial = self.experiment.create_trial(
            hyperparameters={
                'hp0': 's',
                'hp1': 89,
                'hp2': float('inf'),
            },
        )
        self.assertEqual(2, len(responses.calls))
        self.assertEqual({
            'hyperparameters': {
                'hp0': {'s': 's'},
                'hp1': {'i': 89},
                'hp2': {'f': '+Inf'},
            },
            'status': 'QUEUED',
        }, json.loads(responses.calls[1].request.body))
        self.assertEqual(
            schedy.Trial(self.experiment._core,
                         'test-project', 'Test experiment', '.12345',
                         hyperparameters={
                             'hp0': 's',
                             'hp1': 89,
                             'hp2': float('inf')
                         },
                         status='QUEUED',
                         etag='456',
                         ),
            trial
        )

    @responses.activate
    def test_get_trial(self):
        responses.add(
            responses.GET,
            self.experiment._core.routes.trial('test-project', 'Test experiment', '.12345'),
            status=requests.codes.ok,
            body='''{
                "project": "test-project",
                "experiment": "Test experiment",
                "id": ".12345",
                "status": "RUNNING",
                "hyperparameters": {
                    "hp0": {"s": "s"},
                    "hp1": {"i": 89},
                    "hp2": {"f": "+Inf"}
                }
            }''',
            headers={'ETag': '456'},
        )
        trial = self.experiment.get_trial('.12345')
        self.assertEqual(2, len(responses.calls))
        self.assertEqual(
            schedy.Trial(self.experiment._core,
                         'test-project', 'Test experiment', '.12345',
                         hyperparameters={
                             'hp0': 's',
                             'hp1': 89,
                             'hp2': float('inf')
                         },
                         status=schedy.Trial.RUNNING,
                         etag='456',
                         ),
            trial
        )

    @responses.activate
    def test_get_trials(self):
        responses.add(
            responses.GET,
            self.experiment._core.routes.trials('test-project', 'Test experiment'),
            status=requests.codes.ok,
            body='''
            {
                "trials": [
                    {
                        "project": "test-project",
                        "experiment": "Test experiment",
                        "id": ".1",
                        "status": "RUNNING",
                        "hyperparameters": {
                            "hp": {"i": 1}
                        },
                        "metrics": {
                            "m": "-Inf"
                        },
                        "metadata": {
                            "d": {"m": {"v": {"i": 3}}}
                        }
                    },
                    {
                        "project": "test-project",
                        "experiment": "Test experiment",
                        "id": ".2",
                        "status": "RUNNING",
                        "hyperparameters": {
                            "hp": {"i": 2}
                        },
                        "metrics": {
                            "m": "-Inf"
                        },
                        "metadata": {
                            "d": {"m": {"v": {"i": 4}}}
                        }
                    }
                ],
                "end": "end-token"
            }'''
        )
        responses.add(
            responses.GET,
            self.experiment._core.routes.trials('test-project', 'Test experiment'),
            status=requests.codes.ok,
            body='''
            {
                "trials": [
                    {
                        "project": "test-project",
                        "experiment": "Test experiment",
                        "id": ".3",
                        "status": "RUNNING",
                        "hyperparameters": {
                            "hp": {"i": 3}
                        },
                        "metrics": {
                            "m": "-Inf"
                        },
                        "metadata": {
                            "d": {"m": {"v": {"i": 5}}}
                        }
                    },
                    {
                        "project": "test-project",
                        "experiment": "Test experiment",
                        "id": ".4",
                        "status": "RUNNING",
                        "hyperparameters": {
                            "hp": {"i": 4}
                        },
                        "metrics": {
                            "m": "-Inf"
                        },
                        "metadata": {
                            "d": {"m": {"v": {"i": 6}}}
                        }
                    }
                ],
                "end": "end-token-2"
            }'''
        )
        responses.add(
            responses.GET,
            self.experiment._core.routes.trials('test-project', 'Test experiment'),
            status=requests.codes.ok,
            body='''
            {
                "trials": []
            }
            '''
        )
        trials = list(self.experiment.get_trials())
        self.assertEqual(4, len(responses.calls))
        self.assertEqual(len(trials), 4)
        for idx, trial in enumerate(trials):
            self.assertEqual(
                schedy.Trial(
                    self.experiment._core,
                    'test-project',
                    'Test experiment',
                    '.{}'.format(idx + 1),
                    status=schedy.Trial.RUNNING,
                    hyperparameters={'hp': idx + 1},
                    metrics={'m': float('-inf')},
                    metadata={'d': {'v': idx + 3}},
                ),
                trial
            )
        self.assertEqual('start=end-token', urlparse(responses.calls[2].request.url).query)
        self.assertEqual('start=end-token-2', urlparse(responses.calls[3].request.url).query)

    @responses.activate
    def test_disable_trial(self):
        responses.add(
            responses.DELETE,
            self.experiment._core.routes.trial('test-project', 'Test experiment', '.123'),
            status=requests.codes.ok
        )
        self.experiment.delete_trial('.123')
        self.assertEqual(2, len(responses.calls))

