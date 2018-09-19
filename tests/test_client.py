from unittest import TestCase
import json
import responses
import requests
import schedy


class TestClient(TestCase):
    def setUp(self):
        self.client = schedy.Client(config_override={
            'root': 'http://fake.schedy.io/',
            'email': 'test@schedy.io',
            'token': 'testToken',
        })

    @responses.activate
    def test_create_project(self):
        # Signin
        responses.add(
            responses.POST,
            self.client._core.routes.signin,
            body='{"token":"TEST TOKEN","expiresAt":1537432172}',
            content_type='application/json',
            status=requests.codes.ok
        )
        responses.add(
            responses.POST,
            self.client._core.routes.projects,
            status=requests.codes.no_content,
        )
        project = self.client.create_project('id-01', 'My project')
        self.assertEqual(2, len(responses.calls))
        self.assertEqual({
            'projectID': 'id-01',
            'name': 'My project',
        }, json.loads(responses.calls[1].request.body))
        self.assertEqual(schedy.Project(self.client._core, 'id-01', 'My project'), project)

