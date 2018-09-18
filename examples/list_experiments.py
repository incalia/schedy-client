#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

from schedy import Client

if __name__ == '__main__':
    db = Client()
    for exp in db.get_experiments():
        print(exp)
        for job in exp.all_jobs():
            print(job)

