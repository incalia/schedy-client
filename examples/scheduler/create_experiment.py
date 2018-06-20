#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import schedy

db = schedy.SchedyDB()
experiment = schedy.ManualSearch('MinimizeManual')
db.add_experiment(experiment)
