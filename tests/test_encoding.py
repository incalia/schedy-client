# -*- coding: utf-8 -*-

import unittest
from schedy import encoding


class TestEncoding(unittest.TestCase):
    def test_none(self):
        d = encoding._scalar_definition(None)
        self.assertEqual(d, {'n': None})
        self.assertIs(encoding._from_scalar_definition(d), None)

    def test_float(self):
        d = encoding._scalar_definition(2.5)
        self.assertEqual(d, {'f': 2.5})
        self.assertEqual(encoding._from_scalar_definition(d), 2.5)

    def test_int(self):
        d = encoding._scalar_definition(2)
        self.assertEqual(d, {'i': 2})
        self.assertEqual(encoding._from_scalar_definition(d), 2)

    def test_string(self):
        d = encoding._scalar_definition('hello')
        self.assertEqual(d, {'s': 'hello'})
        self.assertEqual(encoding._from_scalar_definition(d), 'hello')

    def test_bytes(self):
        d = encoding._scalar_definition(b'hello')
        self.assertEqual(d, {'d': 'aGVsbG8='})
        self.assertEqual(encoding._from_scalar_definition(d), b'hello')

    def test_bool(self):
        d = encoding._scalar_definition(True)
        self.assertEqual(d, {'b': True})
        self.assertEqual(encoding._from_scalar_definition(d), True)

    def test_map(self):
        d = encoding._scalar_definition({'a': 456, 'b': 456})
        self.assertEqual(d, {'m': {'a': {'i': 456}, 'b': {'i': 456}}})
        self.assertEqual(encoding._from_scalar_definition(d), {'a': 456, 'b': 456})

    def test_list(self):
        d = encoding._scalar_definition(['hello'])
        self.assertEqual(d, {'a': [{'s': 'hello'}]})
        self.assertEqual(encoding._from_scalar_definition(d), ['hello'])
