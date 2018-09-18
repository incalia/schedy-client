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
        self.fail()

    def test__register_scheduler(self):
        self.fail()

    def test_authenticated_request(self):
        self.fail()

    def test__make_session(self):
        self.fail()

    def test__perform_request(self):
        self.fail()


