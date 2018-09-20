# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import responses
import time
import requests


def signin_helper(routes):
    body = '{"token":"TEST TOKEN","expiresAt":'
    body += str(int(time.time()) + 3600)
    body += '}'
    responses.add(
        responses.POST,
        routes.signin,
        body=body,
        content_type='application/json',
        status=requests.codes.ok
    )
