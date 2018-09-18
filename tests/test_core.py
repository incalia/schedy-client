from unittest import TestCase

import schedy
import requests
import datetime
import responses


class TestCore(TestCase):

    def setUp(self):
        config = {'email': 'test@schedy.io', 'token': 'TOKEN', 'type': 'apiToken', 'root': 'http://fake.schedy.io/'}
        self.client = schedy.Client(config_override=config)
        self.dt = datetime.datetime.fromtimestamp(1536745835)

    @responses.activate
    def test__authenticate(self):
        # OK
        responses.add(
            responses.POST,
            self.client.core.routes.signin,
            body='{"token": "test token", "expiresAt": 1536745835}',
            content_type='application/json',
            status=requests.codes.ok
        )
        responses.add(
            responses.POST,
            self.client.core.routes.signin,
            status=requests.codes.forbidden
        )

        self.client.core._authenticate()

        request = responses.calls[0].request
        self.assertEqual('POST', request.method)
        self.assertEqual(b'{"email": "test@schedy.io", "token": "TOKEN", "type": "apiToken"}', request.body)
        self.assertEqual('test token', self.client.core._jwt_token.token_string)
        self.assertEqual(self.dt, self.client.core._jwt_token.expires_at)

        with self.assertRaises(schedy.errors.AuthenticationError):
            self.client.core._authenticate()

    def test_routes(self):
        self.assertEqual('http://fake.schedy.io/', self.client.core.routes.root)
        with self.assertRaises(AttributeError):
            self.client.core.routes.root = 'http://fake_v2.schedy.io/'

        self.assertEqual('http://fake.schedy.io/accounts/signup/', self.client.core.routes.signup)
        self.assertEqual('http://fake.schedy.io/accounts/signin/', self.client.core.routes.signin)
        self.assertEqual('http://fake.schedy.io/accounts/generateToken/', self.client.core.routes.generate_token)
        self.assertEqual('http://fake.schedy.io/accounts/activate/', self.client.core.routes.activate)
        self.assertEqual('http://fake.schedy.io/accounts/disable/', self.client.core.routes.disable)

        self.assertEqual('http://fake.schedy.io/projects/', self.client.core.routes.projects)
        self.assertEqual('http://fake.schedy.io/projects/%2A%C2%A8%C2%A3%25%C2%A3%25M%2B/', self.client.core.routes.project('*¨£%£%M+'))
        self.assertEqual('http://fake.schedy.io/projects/%2A%C2%A8%C2%A3%25%C2%A3%25M%2B/permissions/', self.client.core.routes.project_permissions('*¨£%£%M+'))
        self.assertEqual('http://fake.schedy.io/projects/%2A%C2%A8%C2%A3%25%C2%A3%25M%2B/permissions/test%40schedy.io/', self.client.core.routes.project_permissions_edit('*¨£%£%M+', 'test@schedy.io'))

        self.assertEqual('http://fake.schedy.io/projects/%3C%7C%C2%BA%EA%B0%90%C2%BA%7C%3E/experiments/',
                         self.client.core.routes.experiments('<|º감º|>'))
        self.assertEqual('http://fake.schedy.io/projects/%60%60%3A%24%5Ef123/experiments/-1%20%E2%9C%8C%E2%8A%82%28%E2'
                         '%9C%B0%E2%80%BF%E2%9C%B0%29%E3%81%A4%E2%9C%8C/',
                         self.client.core.routes.experiment('``:$^f123', '-1 ✌⊂(✰‿✰)つ✌'))

        self.assertEqual('http://fake.schedy.io/projects/%60%60%3A%24%5Ef123/experiments/-1%20%E2%9C%8C%E2%8A%82%28%E2'
                         '%9C%B0%E2%80%BF%E2%9C%B0%29%E3%81%A4%E2%9C%8C/schedule',
                         self.client.core.routes.schedule('``:$^f123', '-1 ✌⊂(✰‿✰)つ✌'))

        self.assertEqual('http://fake.schedy.io/projects/%60%60%3A%24%5Ef123/experiments/-1%20%E2%9C%8C%E2%8A%82%28%E2'
                         '%9C%B0%E2%80%BF%E2%9C%B0%29%E3%81%A4%E2%9C%8C/schedulers',
                         self.client.core.routes.schedulers('``:$^f123', '-1 ✌⊂(✰‿✰)つ✌'))

        self.assertEqual('http://fake.schedy.io/projects/project%20123%20%CE%B5%28%C2%B4%EF%AD%81%EF%B8%B5%EF%AD%81%60'
                         '%29%D0%B7/experiments/experiment%20123%20%CE%B5%28%C2%B4%EF%AD%81%EF%B8%B5%EF%AD%81%60%29%D0'
                         '%B7/trials/',
                         self.client.core.routes.trials('project 123 ε(´סּ︵סּ`)з', 'experiment 123 ε(´סּ︵סּ`)з'))

        self.assertEqual('http://fake.schedy.io/projects/project%20%CB%9A%E2%88%86%CB%9A/experiments/exp%20%CB%9A%E2%88'
                         '%86%CB%9A/trials/trial%20%CB%9A%E2%88%86%CB%9A/',
                         self.client.core.routes.trial('project ˚∆˚', 'exp ˚∆˚', 'trial ˚∆˚'))

        self.assertEqual('http://fake.schedy.io/', self.client.core.routes.root)

    def test__register_scheduler(self):
        self.fail()

    def test_authenticated_request(self):
        self.fail()

    def test__make_session(self):
        self.fail()

    def test__perform_request(self):
        self.fail()


