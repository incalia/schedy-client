#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import schedy

db = schedy.SchedyDB()
experiment = db.get_experiment('MinimizeManual')
job = experiment.add_job(hyperparameters={'x': 1, 'y': 2})

