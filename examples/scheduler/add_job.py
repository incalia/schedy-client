#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import *

import schedy

db = schedy.SchedyDB()
experiment = db.get_experiment('MinimizeManual')
job = experiment.add_job(hyperparameters={'x': 1, 'y': 2})

