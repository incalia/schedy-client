from unittest import TestCase

import schedy
import requests
import datetime
import httpretty


class TestSchedyDB(TestCase):

    def setUp(self):
        config = {'email': 'test@schedy.io', 'token': 'TOKEN', 'type': 'apiToken', 'root': 'http://fake.schedy.io/'}
        self.client = schedy.Client(config_override=config)
        self.dt = datetime.datetime.fromtimestamp(1536745835)

    @httpretty.httprettified
    def test_authenticate_ok(self):

        httpretty.register_uri(
            httpretty.POST,
            self.client.core.routes.signin,
            body='{"token": "test token", "expiresAt": 1536745835}',
            content_type='application/json',
            status=requests.codes.ok
        )

        self.client.core._authenticate()
        request = httpretty.last_request()

        self.assertEqual('POST', request.method)
        self.assertEqual(b'{"email": "test@schedy.io", "token": "TOKEN", "type": "apiToken"}', request.body)
        self.assertEqual('test token', self.client.core._jwt_token.token_string)
        self.assertEqual(self.dt, self.client.core._jwt_token.expires_at)

    @httpretty.httprettified
    def test_authenticate_forbidden(self):

        httpretty.register_uri(
            httpretty.POST,
            self.client.core.routes.signin,
            status=requests.codes.forbidden
        )

        with self.assertRaises(schedy.errors.AuthenticationError):
            self.client.core._authenticate()
