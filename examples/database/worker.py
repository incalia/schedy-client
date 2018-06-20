#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import schedy
import random

db = schedy.SchedyDB()
experiment = db.get_experiment('MinimizeSimple')
for i in range(20):
    # Test the problem for random values of x and y, 20 times
    x = random.uniform(-100, 100)
    y = random.uniform(-100, 100)
    result = x ** 2 + y ** 2
    # Tell Schedy about it!
    experiment.add_job(status=schedy.Job.DONE, hyperparameters={'x': x, 'y': y}, results={'result': result})

