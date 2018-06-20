#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

from schedy import SchedyDB

if __name__ == '__main__':
    db = SchedyDB()
    for exp in db.get_experiments():
        print(exp)
        for job in exp.all_jobs():
            print(job)

