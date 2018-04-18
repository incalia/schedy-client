#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import *

import schedy

db = schedy.SchedyDB()
distributions = {
    'x': schedy.random.Normal(0, 5),
    'y': schedy.random.Normal(0, 2),
}
experiment = schedy.RandomSearch('MinimizeRandom', distributions)
db.add_experiment(experiment)

