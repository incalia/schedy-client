from unittest import TestCase
from schedy import Project
from schedy.experiments import Experiment
from schedy.core import Core, Config
import responses
import requests
import json

from .utils import signin_helper


class TestProject(TestCase):

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

        self.core = Core(Config(config_path=None, config=self.config))
        self.project = Project(self.core, self.project_id, self.project_name)
        signin_helper(self.core.routes)

    @responses.activate
    def test_create_experiment(self):
        responses.add(
            responses.POST,
            self.core.routes.experiments('test-12345'),
            body='{"id":"test-12345", "name": "Test 12345"}',
            content_type='application/json',
            status=requests.codes.ok
        )

        self.project.create_experiment(self.exp_name, hyperparameters=['hp0', '明', u'hp2'], metrics=['acc', 'f1'])

        self.assertEqual(2, len(responses.calls))

        request_2 = responses.calls[1].request

        content = {
            'name': 'Experiment name',
            'hyperparameters': [{'name': 'hp0'}, {'name': '明'}, {'name': 'hp2'}],
            'metricsName': ['acc', 'f1'],
        }

        self.assertDictEqual(content, json.loads(request_2.body))

    @responses.activate
    def test_get_experiment(self):
        responses.add(
            responses.GET,
            self.core.routes.experiment(self.project_id, self.exp_name),
            json={"projectID": "test-12345", "name": "Test 12345", "hyperparameters": [
                {"name": "layers"},
                {"name": "activation"},
                {"name": "layer sizes"},
            ], "metricsName": ['f1 score', 'accuracy']},
            status=requests.codes.ok
        )
        exp = self.project.get_experiment('Experiment name')
        expected_experiment = Experiment(self.core, self.project_id, self.project_name,
                                         hyperparameters=['layers', 'activation', 'layer sizes'],
                                         metrics=['f1 score', 'accuracy'])

        self.assertEqual(2, len(responses.calls))

        request_2 = responses.calls[1].request

        self.assertEqual('GET', request_2.method)
        self.assertEqual(repr(expected_experiment), repr(exp))

    @responses.activate
    def test_delete_experiment(self):
        responses.add(
            responses.DELETE,
            self.core.routes.experiment(self.project_id, self.exp_name),
            body='',
            content_type='application/json',
            status=requests.codes.no_content
        )

        self.project.delete_experiment(self.exp_name)

        self.assertEqual(None, responses.calls[1].request.body)
        self.assertEqual(responses.DELETE, responses.calls[1].request.method)

    @responses.activate
    def test_get_experiments(self):
        responses.add(
            responses.GET,
            self.core.routes.experiments(self.project_id),
            json={
                "experiments": [
                    {"projectID": "test-12345", "name": "Test 12345", "hyperparameters": [
                        {"name": "layers"},
                        {"name": "activation"},
                        {"name": "layer sizes"},
                    ], "metricsName": ['f1 score', 'accuracy']}
                ],
                "end": "NEXT TOKEN TEST"
            },
            status=requests.codes.ok
        )

        exp_iterator = self.project.get_experiments()
        exp = next(exp_iterator)

        expected_experiment = Experiment(self.core, self.project_id,
                                         self.project_name,
                                         hyperparameters=[
                                             'layers',
                                             'activation',
                                             'layer sizes'
                                         ],
                                         metrics=[
                                             'f1 score',
                                             'accuracy'
                                         ],
                                         )

        self.assertEqual('GET', responses.calls[1].request.method)
        self.assertEqual(expected_experiment, exp)
        self.assertEqual(2, len(responses.calls))

        responses.reset()

        responses.add(
            responses.GET,
            self.core.routes.experiments(self.project_id),
            json={
                "experiments": [],
                "end": "NEXT TOKEN TEST"
            },
            status=requests.codes.ok
        )

        with self.assertRaises(StopIteration):
            next(exp_iterator)
