#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import schedy
import random

db = schedy.SchedyDB()
experiment = db.get_experiment('MinimizeSimple')
for i in range(20):
    # Test the problem for random values of x and y, 20 times
    x = random.uniform(-10, 10)
    y = random.uniform(-10, 10)
    result = x ** 2 + y ** 2
    # Tell Schedy about it!
    experiment.add_job(status=schedy.JOB_DONE, hyperparameters={'x': x, 'y': y}, results={'result': result})
