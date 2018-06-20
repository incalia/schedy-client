#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import schedy
import json
from tabulate import tabulate
import getpass
from requests.compat import urljoin
import os
import stat
import errno
from six.moves import input
from .compat import json_dumps

DEFAULT_CATEGORY = 'schedy'

def setup_add(subparsers):
    parser = subparsers.add_parser('add', help='Add an experiment.')
    parser.set_defaults(func=cmd_add)
    parser.add_argument('experiment', help='Name for the new experiment.')
    parser.add_argument('-s', '--status', default=schedy.Experiment.RUNNING, choices=(schedy.Experiment.RUNNING, schedy.Experiment.DONE), help='Status of the new experiment.')
    sched_subparsers = parser.add_subparsers(title='Schedulers', dest='scheduler', help='Scheduler type (manual search, random search...)')
    sched_subparsers.required = True
    # Manual scheduling
    sched_subparsers.add_parser('manual', help='Manual search')
    # Random search
    random_parser = sched_subparsers.add_parser('random', help='Random search')
    RANDOM_HP_HELP = (
        'List of the hyperparameters. Each hyperparameter consists in three arguments: name distribution params. '
        '"name" is the name of the hyperparameter. '
        '"distribution" is a distribution among: {}. '
        '"params" is the JSON value for the parameters of the distribution. '
        'Example: learning_rate loguniform \'{{"base": 10, "lowExp": -1, "highExp": 5}}\' num_lays choice \'{{"values": [5, 6, 7, 8]}}\''
    ).format(', '.join(schedy.random._DISTRIBUTION_TYPES.keys()))
    random_parser.add_argument('hyperparameters', nargs='+', help=RANDOM_HP_HELP)
    random_parser.set_defaults(parser=random_parser)

def cmd_add(args):
    db = schedy.SchedyDB(config_path=args.config)
    if args.scheduler == 'manual':
        exp = schedy.ManualSearch(args.experiment, status=args.status)
    elif args.scheduler == 'random':
        if len(args.hyperparameters) % 3 != 0:
            args.parser.error('Invalid hyperparameters (not a list of name/distribution/params).')
        hyperparameters = {}
        for i in range(0, len(args.hyperparameters), 3):
            name = args.hyperparameters[i]
            dist_name = args.hyperparameters[i + 1]
            params_txt = args.hyperparameters[i + 2]
            if name in hyperparameters:
                args.parser.error('Duplicate hyperparameter: {}.'.format(name))
            try:
                dist_type = schedy.random._DISTRIBUTION_TYPES[dist_name]
            except KeyError:
                args.parser.error('Invalid distribution: {}.'.format(dist_name))
            try:
                params = json.loads(params_txt)
                hyperparameters[name] = dist_type._from_args(params)
            except (TypeError, ValueError, KeyError) as e:
                args.parser.error('Invalid distribution parameters for {} ({!r}).'.format(name, e))
        exp = schedy.RandomSearch(args.experiment, status=args.status, distributions=hyperparameters)
    db.add_experiment(exp)

def setup_rm(subparsers):
    parser = subparsers.add_parser('rm', help='Remove an experiment or a job.')
    parser.set_defaults(func=cmd_rm)
    parser.add_argument('experiment', help='Name of the experiment.')
    parser.add_argument('job', nargs='?', help='Name of the job.')
    parser.add_argument('-f', '--force', action='store_true', help='Don\'t ask for confirmation.')

def cmd_rm(args):
    db = schedy.SchedyDB(config_path=args.config)
    exp = db.get_experiment(args.experiment)
    if args.job is None:
        if not args.force:
            print_exp(exp)
            confirmation = input('Are you sure you want to remove {} and all its jobs? [y/N] '.format(exp.name))
            if confirmation.lower() != 'y':
                print('{} was not removed.'.format(exp.name))
                return
        exp.delete()
    else:
        job = exp.get_job(args.job)
        if not args.force:
            print_job(job)
            confirmation = input('Are you sure you want to remove {}? [y/N] '.format(job.job_id))
            if confirmation.lower() != 'y':
                print('{} was not removed.'.format(job.job_id))
                return
        job.delete()

def setup_show(subparsers):
    parser = subparsers.add_parser('show', help='Show an experiment/a job.')
    parser.set_defaults(func=cmd_show)
    parser.add_argument('experiment', help='Name for the new experiment.')
    parser.add_argument('job', nargs='?', help='Name of the job.')

def cmd_show(args):
    db = schedy.SchedyDB(config_path=args.config)
    exp = db.get_experiment(args.experiment)
    if args.job is None:
        print_exp(exp)
    else:
        job = exp.get_job(args.job)
        print_job(job)

def setup_list(subparsers):
    parser = subparsers.add_parser('list', help='List experiments/jobs (by default, lists all experiments).')
    parser.set_defaults(func=cmd_list, parser=parser)
    parser.add_argument('experiment', nargs='?', help='Name of the experiment whose jobs will be listed.')
    parser.add_argument('-t', '--table', action='store_true', help='Long description, as a table.')
    parser.add_argument('-p', '--paragraph', action='store_true', help='Long description, as a series of paragraphs.')
    parser.add_argument('-s', '--sort', action='append', help='Field by which we should sort. You can specify multiple fields using this argument multiple times.')
    parser.add_argument('-d', '--decreasing', action='store_true', help='Sort in reverse order (decreasing values).')
    parser.add_argument('-f', '--field', action='append', help='Specify this option multiple times to select the fields you want to diply (all by default).')

def cmd_list(args):
    db = schedy.SchedyDB(config_path=args.config)
    if args.experiment is None:
        experiments = db.get_experiments()
        table = exp_table(experiments)
    else:
        exp = db.get_experiment(args.experiment)
        jobs = exp.all_jobs()
        table = job_table(jobs)
    if args.sort is not None:
        try:
            table.sort(args.sort, reverse=args.decreasing)
        except KeyError as e:
            args.parser.error(str(e))
    if args.field is not None:
        table.filter_fields(args.field)
    if args.table:
        table.print_table()
    elif args.paragraph:
        table.print_paragraphs()
    else:
        if args.field is None:
            table.filter_categories([DEFAULT_CATEGORY])
        table.print_table('plain', include_headers=False)

def setup_push(subparsers):
    parser = subparsers.add_parser('push', help='Manually add a job to an existing experiment.')
    parser.set_defaults(func=cmd_push)
    parser.add_argument('experiment', help='Name of the experiment for the job.')
    parser.add_argument('-s', '--status', choices=(schedy.Job.QUEUED, schedy.Job.RUNNING, schedy.Job.DONE, schedy.Job.CRASHED, schedy.Job.PRUNED), help='Status of the job.')
    parser.add_argument('-r', '--results', nargs='+', help='Optional results for the job. Each result must be provided as a pair: name value. value must be a valid JSON value. For example: -r accuracy 0.9 loss_history \'[0.9, 0.8, 0.7]\'')
    parser.add_argument('-p', '--hyperparameters', nargs='+', required=True, help='Hyperparameters for the job. Each hyperparameter must be provided as a pair: name value. value must be a valid JSON value. For example: -p learning_rate 0.01 num_layers 3 size_layers \'[512, 1024, 512]\'')
    parser.set_defaults(parser=parser)

def cmd_push(args):
    db = schedy.SchedyDB(config_path=args.config)
    kwargs = dict()
    # Status
    if args.status is not None:
        kwargs['status'] = args.status
    # Results
    if args.results is not None:
        if len(args.results) % 2 != 0:
            args.parser.error('Invalid results (not a list of name/value).')
        results = dict()
        for i in range(0, len(args.results), 2):
            name = args.results[i]
            value_txt = args.results[i + 1]
            if name in results:
                args.parser.error('Duplicate result: {}.'.format(name))
            try:
                results[name] = json.loads(value_txt)
            except (TypeError, ValueError) as e:
                args.parser.error('Invalid value for result {} ({!r}).'.format(name, e))
        kwargs['results'] = results
    # Hyperparameters
    if len(args.hyperparameters) % 2 != 0:
        args.parser.error('Invalid hyperparameters (not a list of name/value).')
    hyperparameters = dict()
    for i in range(0, len(args.hyperparameters), 2):
        name = args.hyperparameters[i]
        value_txt = args.hyperparameters[i + 1]
        if name in hyperparameters:
            args.parser.error('Duplicate hyperparameter: {}.'.format(name))
        try:
            hyperparameters[name] = json.loads(value_txt)
        except (TypeError, ValueError) as e:
            args.parser.error('Invalid value for hyperparameter {} ({!r}).'.format(name, e))
    kwargs['hyperparameters'] = hyperparameters
    exp = db.get_experiment(args.experiment)
    job = exp.add_job(**kwargs)
    print_job(job)

def setup_gen_token(subparsers):
    parser = subparsers.add_parser('gen-token', help='Generate and save a new API token (i.e. configuration file).')
    parser.set_defaults(func=cmd_gen_token)
    parser.add_argument('--root', default='https://api.schedy.io/', help='Schedy API root URL.')
    parser.add_argument('--email', help='User email (prompted if not provided).')
    parser.add_argument('--password', help='User password (prompted if not provided).')

def cmd_gen_token(args):
    config = {
        'root': args.root,
        'token_type': 'password',
    }
    if args.email is None:
        config['email'] = input('Email: ')
    else:
        config['email'] = args.email
    if args.password is None:
        config['token'] = getpass.getpass('Password: ')
    else:
        config['token'] = args.password
    db = schedy.SchedyDB(config_override=config)
    url = urljoin(db.root, 'resettoken/')
    response = db._authenticated_request('POST', url=url)
    schedy.errors._handle_response_errors(response)
    new_content = response.json()
    if args.config is None:
        config_path = schedy.core._default_config_path()
    else:
        config_path = args.config
    config_dir = os.path.dirname(config_path)
    if config_dir:
        try:
            os.makedirs(config_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            pass
    with open(config_path, 'w') as config_file:
        config_file.write(json_dumps(new_content, cls=schedy.encoding.SchedyJSONEncoder))
    try:
        os.chmod(config_path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        print('Token file permissions could not be set.')
    print('Your token has been saved to {}.'.format(config_path))

def main():
    parser = argparse.ArgumentParser(description='Manage your Schedy jobs.')
    parser.add_argument('--config', type=str, help='Schedy configuration file.')
    subparsers = parser.add_subparsers(title='Commands', dest='command')
    subparsers.required = True
    setup_add(subparsers)
    setup_rm(subparsers)
    setup_show(subparsers)
    setup_list(subparsers)
    setup_push(subparsers)
    setup_gen_token(subparsers)
    args = parser.parse_args()
    args.func(args)

class TableData(object):
    def __init__(self):
        self.headers = list()
        self.rows = list()

    def add_row(self, data):
        row = [None] * len(self.headers)
        for key, value in data.items():
            try:
                idx = self.headers.index(key)
            except ValueError:
                idx = len(self.headers)
                self.headers.append(key)
            if idx >= len(row):
                row.extend([None] * (idx - len(row) + 1))
            row[idx] = value
        self.rows.append(row)

    def header_names(self, explicit=False):
        used_names = dict()
        if not explicit:
            expand = [False] * len(self.headers)
            for idx, (category, name) in enumerate(self.headers):
                withoutexp = used_names.setdefault(name, idx)
                withexp = used_names.setdefault(category + '.' + name, idx)
                if withoutexp != idx:
                    expand[idx] = True
                    expand[withoutexp] = True
                if withexp != idx:
                    expand[idx] = True
                    expand[withoutexp] = True
        else:
            expand = [True] * len(self.headers)
        names = []
        for (category, name), should_expand in zip(self.headers, expand):
            if should_expand:
                names.append(category + '.' + name)
            else:
                names.append(name)
        return names

    def _get_fields_indices(self, fields):
        indices = []
        for field in fields:
            try:
                indices.append(self.header_names(explicit=True).index(field))
            except ValueError:
                try:
                    indices.append(self.header_names(explicit=False).index(field))
                except ValueError:
                    raise KeyError('Field "{}" not found or ambiguous.'.format(field))
        return indices

    def _filter_columns(self, indices):
        self.rows = [[row[idx] if idx < len(row) else None for idx in indices] for row in self.rows]
        self.headers = [self.headers[idx] for idx in indices]

    def sort(self, fields, reverse=False):
        indices = self._get_fields_indices(fields)
        def key_func(row):
            key = tuple()
            for idx in indices:
                if idx < len(row):
                    val = row[idx]
                else:
                    val = None
                # Always put None at the end
                if val is None:
                    key = key + (not reverse, None)
                else:
                    key = key + (reverse, val)
            return key
        self.rows = sorted(self.rows, key=key_func, reverse=reverse)

    def filter_categories(self, categories):
        fields_idx = [idx for idx, (cat, _) in enumerate(self.headers) if cat in categories]
        self._filter_columns(fields_idx)

    def filter_fields(self, fields):
        indices = self._get_fields_indices(fields)
        self._filter_columns(indices)

    def print_paragraphs(self):
        fields = self.header_names()
        for i in range(len(self.rows)):
            row = self.rows[i]
            for field, value in zip(fields, row):
                if value is not None:
                    print('{}: {}'.format(field, value))
            if i != len(self.rows) - 1:
                print()

    def print_table(self, fmt='psql', include_headers=True):
        if include_headers:
            print(tabulate(self.rows, self.header_names(), tablefmt=fmt))
        else:
            print(tabulate(self.rows, tablefmt=fmt))

def exp_table(experiments):
    data = TableData()
    for exp in experiments:
        row = {
            (DEFAULT_CATEGORY, 'name'): exp.name,
            (DEFAULT_CATEGORY, 'status'): exp.status,
            (DEFAULT_CATEGORY, 'scheduler'): exp._SCHEDULER_NAME,
        }
        if isinstance(exp, schedy.RandomSearch):
            for name, dist in exp.distributions.items():
                row[('hyperparameter', name)] = '{} ({})'.format(dist._FUNC_NAME, json_dumps(dist._args(), cls=schedy.encoding.SchedyJSONEncoder))
        data.add_row(row)
    return data

def job_table(jobs):
    data = TableData()
    for job in jobs:
        row = {
            (DEFAULT_CATEGORY, 'id'): job.job_id,
            (DEFAULT_CATEGORY, 'status'): job.status,
        }
        for name, value in job.hyperparameters.items():
            row[('hyperparameter', name)] = value
        if job.results is not None:
            for name, value in job.results.items():
                row[('result', name)] = value
        data.add_row(row)
    return data

def print_exp(exp):
    exp_table([exp]).print_paragraphs()

def print_job(job):
    job_table([job]).print_paragraphs()

if __name__ == '__main__':
    main()

