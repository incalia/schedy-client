# -*- coding: utf-8 -*-

import unittest
import numpy as np
import schedy


class TestNumpyIntegration(unittest.TestCase):
    def test_numpy_array(self):
        buf = schedy.compat.json_dumps(np.ones(5, dtype=np.int_), cls=schedy.encoding.JSONEncoder)
        self.assertEqual(buf, '[1, 1, 1, 1, 1]')

    def test_numpy_generic(self):
        buf = schedy.compat.json_dumps(np.bool_(0), cls=schedy.encoding.JSONEncoder)
        self.assertEqual(buf, 'false')
