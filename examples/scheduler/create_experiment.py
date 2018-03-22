#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import schedy

db = schedy.SchedyDB()
experiment = schedy.ManualSearch('MinimizeManual')
db.add_experiment(experiment)
