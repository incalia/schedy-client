# -*- coding: utf-8 -*-

from unittest import TestCase

import schedy.cmd
from schedy.cmd import cmd_gen_token
from collections import namedtuple
import os
import requests
import schedy
import responses
import json
import tempfile

Args = namedtuple('args', ['root', 'token_type', 'email', 'password', 'config'])


class TestCmd(TestCase):
    def setUp(self):
        self._tmp_config_file = os.path.join(tempfile.gettempdir(), '.schedy/client.json')
        self._root = 'http://fake.schedy.io/'
        self._email = 'test@schedy.io'
        self._generated_token = 'GENERATED TOKEN'
        self.routes = schedy.core._Routes(self._root)

    def tearDown(self):
        os.remove(self._tmp_config_file)

    @responses.activate
    def test_cmd_gen_token(self):

        responses.add(
            responses.POST,
            self.routes.signin,
            json={"token": "test token", "expiresAt": 1536745835},
            content_type='application/json',
            status=requests.codes.ok
        )

        responses.add(
            responses.POST,
            self.routes.generate_token,
            json={'token': self._generated_token},
            content_type='application/json',
            status=requests.codes.ok
        )

        args = Args(self._root, token_type='password', email=self._email, password='PASSWORD', config=self._tmp_config_file)

        cmd_gen_token(args)

        with open(self._tmp_config_file) as f:
            config = json.load(f)
            self.assertDictEqual({
                'token': 'GENERATED TOKEN',
                'root': self._root,
                'email': self._email,
                'token_type': 'apiToken'}, config)
