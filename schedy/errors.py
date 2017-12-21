# -*- coding: utf-8 -*-

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

class ClientRequestError(ClientError):
    pass

class ResourceExistsError(ClientRequestError):
    pass

class UnhandledResponseError(ClientError):
    pass

class ServerError(HTTPError):
    pass

