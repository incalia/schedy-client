from unittest import TestCase
import json
import responses
import requests
from requests.compat import urlparse
import schedy
from .test_utils import signin_helper


class TestClient(TestCase):
    def setUp(self):
        self.client = schedy.Client(config_override={
            'root': 'http://fake.schedy.io/',
            'email': 'test@schedy.io',
            'token': 'testToken',
        })
        signin_helper(self.client._core.routes)

    @responses.activate
    def test_create_project(self):
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

    @responses.activate
    def test_get_project(self):
        responses.add(
            responses.GET,
            self.client._core.routes.project('id-01'),
            status=requests.codes.ok,
            body='''{
                "id": "id-01",
                "name": "My project"
            }'''
        )
        project = self.client.get_project('id-01')
        self.assertEqual(2, len(responses.calls))
        self.assertEqual(schedy.Project(self.client._core, 'id-01', 'My project'), project)

    @responses.activate
    def test_get_projects(self):
        responses.add(
            responses.GET,
            self.client._core.routes.projects,
            status=requests.codes.ok,
            body='''
            {
                "projects": [
                    {
                        "id": "id-01",
                        "name": "My project 1"
                    },
                    {
                        "id": "id-02",
                        "name": "My project 2"
                    }
                ],
                "end": "end-token"
            }'''
        )
        responses.add(
            responses.GET,
            self.client._core.routes.projects,
            status=requests.codes.ok,
            body='''
            {
                "projects": [
                    {
                        "id": "id-03",
                        "name": "My project 3"
                    },
                    {
                        "id": "id-04",
                        "name": "My project 4"
                    }
                ],
                "end": "end-token-2"
            }'''
        )
        responses.add(
            responses.GET,
            self.client._core.routes.projects,
            status=requests.codes.ok,
            body='''
            {
                "projects": []
            }
            '''
        )
        projects = list(self.client.get_projects())
        self.assertEqual(4, len(responses.calls))
        self.assertEqual(len(projects), 4)
        for idx, project in enumerate(projects):
            self.assertEqual(
                schedy.Project(
                    self.client._core,
                    'id-0{}'.format(idx + 1),
                    'My project {}'.format(idx + 1)
                ),
                project
            )
        self.assertEqual('start=end-token', urlparse(responses.calls[2].request.url).query)
        self.assertEqual('start=end-token-2', urlparse(responses.calls[3].request.url).query)

    @responses.activate
    def test_delete_project(self):
        responses.add(
            responses.DELETE,
            self.client._core.routes.project('id-01'),
            status=requests.codes.ok
        )
        self.client.delete_project('id-01')
        self.assertEqual(2, len(responses.calls))

