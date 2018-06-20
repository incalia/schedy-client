# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import requests

class SchedyError(Exception):
    '''
    Base class for all Schedy exceptions.
    '''
    pass

class HTTPError(SchedyError):
    '''
    Base class for exceptions caused by a transaction with the service.
    '''
    def __init__(self, body, code, *args):
        '''
        Args:
            body (str): Error message.
            code (int or None): HTTP status code.
            args (list): Other arguments passed to :py:exc:`Exception`.
        '''
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
        super(HTTPError, self).__init__(message, *args)

class ClientError(HTTPError):
    '''
    Exception caused by the client side.
    '''
    pass

class ClientRequestError(ClientError):
    '''
    Exception caused by the content of the request.
    '''
    pass

class AuthenticationError(ClientRequestError):
    '''
    Authentication error, access to the resource is forbidden.
    '''
    pass

class ReauthenticateError(ClientRequestError):
    '''
    Authentication error, the client should retry after authenticating again.
    '''
    pass

class ResourceExistsError(ClientRequestError):
    '''
    The resource cannot be created because it exists already.
    '''
    pass

class UnsafeUpdateError(ClientRequestError):
    '''
    The resource cannot be updated safely because it has been modified by
    another client since its state was retrieved, so updating it could
    overwrite these modifications.
    '''
    pass

class NoJobError(ClientRequestError):
    '''
    The request could not return any job.
    '''
    pass

class UnhandledResponseError(ClientError):
    '''
    The response could not be parsed or handled.
    '''
    pass

class ServerError(HTTPError):
    '''
    Server-side exception.
    '''
    pass

def _handle_response_errors(response):
    code = response.status_code
    if code in [200, 201, 204]:
        return
    if code == requests.codes.forbidden:
        raise AuthenticationError(response.text, code)
    if code == requests.codes.unauthorized:
        raise ReauthenticateError(response.text, code)
    if code == requests.codes.precondition_failed:
        raise UnsafeUpdateError(response.text, code)
    if code in range(400, 500):
        raise ClientRequestError(response.text, code)
    if code in range(500, 600):
        raise ServerError(response.text, code)
    raise UnhandledResponseError(response.text, code)

