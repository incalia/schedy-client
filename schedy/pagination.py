# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from six import raise_from

import warnings

from . import errors

_EXPECTED_PAGE_KEYS = {'items', 'next'}

class PageObjectsIterator(object):
    def __init__(self, reqfunc, obj_creation_func):
        self._reqfunc = reqfunc
        self._create_obj = obj_creation_func
        self._next_token = None
        self._items = []
        self._get_page()

    def __iter__(self):
        return self

    def __next__(self):
        if len(self._items) == 0:
            if self._next_token is None:
                raise StopIteration
            self._get_page(self._next_token)
            if len(self._items) == 0:
                raise StopIteration
        cur_item = self._create_obj(self._items[0])
        self._items = self._items[1:]
        return cur_item

    # Python 2 support
    next = __next__

    def _get_page(self, start_token=None):
        if start_token is None:
            params = dict()
        else:
            params = {'start': start_token}
        response = self._reqfunc(params)
        errors._handle_response_errors(response)
        try:
            result = dict(response.json())
        except ValueError as e:
            raise_from(errors.UnhandledResponseError('Expected page as a dict.'), e)
        if result.keys() > _EXPECTED_PAGE_KEYS:
            warnings.warn('Unexpected page keys: {}.'.format(result.keys() - _EXPECTED_PAGE_KEYS))
        try:
            self._items = list(result['items'])
            next_token = result.get('next')
            if next_token is not None:
                self._next_token = str(next_token)
            else:
                self._next_token = None
        except (ValueError, KeyError) as e:
            raise_from(errors.UnhandledResponseError('Invalid page received.'), e)

