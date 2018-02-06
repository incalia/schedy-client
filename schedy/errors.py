# -*- coding: utf-8 -*-

import requests

class SchedyError(Exception):
    pass

class HTTPError(SchedyError):
    def __init__(self, body, code, *args):
        self.code = code
        self.body = body
        # Truncate long bodies
        msg_body = body
        msg_body = msg_body.replace('\r', '')
        msg_body = msg_body.rstrip('\n')
        if len(msg_body) == 0:
            msg_body = '<No server message>'
        elif len(msg_body) > 150:
            msg_body = msg_body[:147] + '...'
        msg_body = msg_body.replace('\n', '\n> ')
        message = 'HTTP Error {}:\n> {}'.format(code, msg_body)
        super().__init__(message, *args)

class ClientError(HTTPError):
    pass

class AuthenticationError(ClientError):
    pass

class ReauthenticateError(ClientError):
    pass

class ClientRequestError(ClientError):
    pass

class ResourceExistsError(ClientRequestError):
    pass

class NoJobError(ClientRequestError):
    pass

class UnhandledResponseError(ClientError):
    pass

class ServerError(HTTPError):
    pass

def _handle_response_errors(response):
    code = response.status_code
    if code in [200, 201, 204]:
        return
    if code == requests.codes.forbidden:
        raise AuthenticationError(response.text, code)
    if code == requests.codes.unauthorized:
        raise ReauthenticateError(response.text, code)
    if code in range(400, 500):
        raise ClientRequestError(response.text, code)
    if code in range(500, 600):
        raise ServerError(response.text, code)
    raise UnhandledResponseError(response.text, code)

