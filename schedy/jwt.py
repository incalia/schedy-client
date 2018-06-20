# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import requests
import datetime

_PRE_EXPIRATION_TIME = datetime.timedelta(minutes=1)
_PRE_EXPIRATION_RATIO = 0.95

class JWTTokenAuth(requests.auth.AuthBase):
    def __init__(self, token_string, expires_at):
        self.token_string = token_string
        self.expires_at = expires_at
        cur_time = datetime.datetime.now()
        self._pre_expiration = max(
            self.expires_at - _PRE_EXPIRATION_TIME,
            cur_time + datetime.timedelta(seconds=(self.expires_at - cur_time).total_seconds() * _PRE_EXPIRATION_RATIO),
        )

    def __call__(self, request):
        request.headers['Authorization'] = 'Bearer ' + self.token_string
        return request

    def is_expired(self):
        return datetime.datetime.now() >= self.expires_at

    def expires_soon(self):
        return datetime.datetime.now() >= self._pre_expiration

