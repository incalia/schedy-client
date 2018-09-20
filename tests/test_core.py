# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

from unittest import TestCase

import schedy
import requests
import datetime
import responses
import json


class TestCore(TestCase):

    def setUp(self):
        self.client = schedy.Client(config_override={'email': 'test@schedy.io', 'token': 'TOKEN', 'type': 'apiToken', 'root': 'http://fake.schedy.io/'})
        self.dt = datetime.datetime.fromtimestamp(1536745835)

    @responses.activate
    def test_authenticate(self):
        # OK
        responses.add(
            responses.POST,
            self.client._core.routes.signin,
            body='{"token": "test token", "expiresAt": 1536745835}',
            content_type='application/json',
            status=requests.codes.ok
        )
        responses.add(
            responses.POST,
            self.client._core.routes.signin,
            status=requests.codes.forbidden
        )

        self.client._core._authenticate()

        request = responses.calls[0].request
        self.assertEqual('POST', request.method)
        self.assertEqual({'email': 'test@schedy.io', 'token': 'TOKEN', 'type': 'apiToken'}, json.loads(request.body))
        self.assertEqual('test token', self.client._core._jwt_token.token_string)
        self.assertEqual(self.dt, self.client._core._jwt_token.expires_at)

        with self.assertRaises(schedy.errors.AuthenticationError):
            self.client._core._authenticate()

    def test_routes(self):
        self.assertEqual('http://fake.schedy.io/', self.client._core.routes.root)
        with self.assertRaises(AttributeError):
            self.client._core.routes.root = 'http://fake_v2.schedy.io/'

        self.assertEqual('http://fake.schedy.io/accounts/signup/', self.client._core.routes.signup)
        self.assertEqual('http://fake.schedy.io/accounts/signin/', self.client._core.routes.signin)
        self.assertEqual('http://fake.schedy.io/accounts/generateToken/', self.client._core.routes.generate_token)
        self.assertEqual('http://fake.schedy.io/accounts/activate/', self.client._core.routes.activate)
        self.assertEqual('http://fake.schedy.io/accounts/disable/', self.client._core.routes.disable)

        self.assertEqual('http://fake.schedy.io/projects/', self.client._core.routes.projects)
        self.assertEqual('http://fake.schedy.io/projects/%2A%C2%A8%C2%A3%25%C2%A3%25M%2B/', self.client._core.routes.project('*¨£%£%M+'))
        self.assertEqual('http://fake.schedy.io/projects/%2A%C2%A8%C2%A3%25%C2%A3%25M%2B/permissions/', self.client._core.routes.project_permissions('*¨£%£%M+'))
        self.assertEqual('http://fake.schedy.io/projects/%2A%C2%A8%C2%A3%25%C2%A3%25M%2B/permissions/test%40schedy.io/', self.client._core.routes.project_permissions_edit('*¨£%£%M+', 'test@schedy.io'))

        self.assertEqual('http://fake.schedy.io/projects/%3C%7C%C2%BA%EA%B0%90%C2%BA%7C%3E/experiments/',
                         self.client._core.routes.experiments('<|º감º|>'))
        self.assertEqual('http://fake.schedy.io/projects/%60%60%3A%24%5Ef123/experiments/-1%20%E2%9C%8C%E2%8A%82%28%E2'
                         '%9C%B0%E2%80%BF%E2%9C%B0%29%E3%81%A4%E2%9C%8C/',
                         self.client._core.routes.experiment('``:$^f123', '-1 ✌⊂(✰‿✰)つ✌'))

        self.assertEqual('http://fake.schedy.io/projects/%60%60%3A%24%5Ef123/experiments/-1%20%E2%9C%8C%E2%8A%82%28%E2'
                         '%9C%B0%E2%80%BF%E2%9C%B0%29%E3%81%A4%E2%9C%8C/schedule',
                         self.client._core.routes.schedule('``:$^f123', '-1 ✌⊂(✰‿✰)つ✌'))

        self.assertEqual('http://fake.schedy.io/projects/%60%60%3A%24%5Ef123/experiments/-1%20%E2%9C%8C%E2%8A%82%28%E2'
                         '%9C%B0%E2%80%BF%E2%9C%B0%29%E3%81%A4%E2%9C%8C/schedulers',
                         self.client._core.routes.schedulers('``:$^f123', '-1 ✌⊂(✰‿✰)つ✌'))

        self.assertEqual('http://fake.schedy.io/projects/project%20123%20%CE%B5%28%C2%B4%EF%AD%81%EF%B8%B5%EF%AD%81%60'
                         '%29%D0%B7/experiments/experiment%20123%20%CE%B5%28%C2%B4%EF%AD%81%EF%B8%B5%EF%AD%81%60%29%D0'
                         '%B7/trials/',
                         self.client._core.routes.trials('project 123 ε(´סּ︵סּ`)з', 'experiment 123 ε(´סּ︵סּ`)з'))

        self.assertEqual('http://fake.schedy.io/projects/project%20%CB%9A%E2%88%86%CB%9A/experiments/exp%20%CB%9A%E2%88'
                         '%86%CB%9A/trials/trial%20%CB%9A%E2%88%86%CB%9A/',
                         self.client._core.routes.trial('project ˚∆˚', 'exp ˚∆˚', 'trial ˚∆˚'))

        self.assertEqual('http://fake.schedy.io/', self.client._core.routes.root)

