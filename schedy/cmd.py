#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import schedy
import json

def setup_add(subparsers):
    parser = subparsers.add_parser('add', help='Add an experiment.')
    parser.set_defaults(func=cmd_add)
    parser.add_argument('experiment', help='Name for the new experiment.')
    parser.add_argument('-s', '--status', default=schedy.EXPERIMENT_RUNNING, choices=(schedy.EXPERIMENT_RUNNING, schedy.EXPERIMENT_DONE), help='Status of the new experiment.')
    sched_subparsers = parser.add_subparsers(title='Schedulers', dest='scheduler', help='Scheduler type (manual search, random search...)')
    sched_subparsers.required = True
    # Manual scheduling
    manual_parser = sched_subparsers.add_parser('manual', help='Manual search')
    # Random search
    random_parser = sched_subparsers.add_parser('random', help='Random search')
    RANDOM_HP_HELP = (
        'List of the hyperparameters. Each hyperparameter consists in three arguments: name distribution params. '
        '"name" is the name of the hyperparameter. '
        '"distribution" is a distribution among: {}. '
        '"params" is the JSON value for the parameters of the distribution. '
        'Example: learning_rate loguniform \'{{"base": 10, "lowExp": -1, "highExp": 5}}\' num_lays choice \'{{"values": [5, 6, 7, 8]}}\''
    ).format(', '.join(schedy.random.DISTRIBUTION_TYPES.keys()))
    random_parser.add_argument('hyperparameters', nargs='+', help=RANDOM_HP_HELP)
    random_parser.set_defaults(parser=random_parser)

def cmd_add(db, args):
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
                dist_type = schedy.random.DISTRIBUTION_TYPES[dist_name]
            except KeyError:
                args.parser.error('Invalid distribution: {}.'.format(dist_name))
            try:
                params = json.loads(params_txt)
                hyperparameters[name] = dist_type.from_args(params)
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

def cmd_rm(db, args):
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

def cmd_show(db, args):
    exp = db.get_experiment(args.experiment)
    if args.job is None:
        print_exp(exp)
    else:
        job = exp.get_job(args.job)
        print_job(job)

def setup_list(subparsers):
    parser = subparsers.add_parser('list', help='List experiments/jobs (by default, lists all experiments).')
    parser.set_defaults(func=cmd_list)
    parser.add_argument('experiment', nargs='?', help='Name of the experiment whose jobs will be listed.')
    parser.add_argument('-l', '--long', action='store_true', help='Long description for each experiment.')

def cmd_list(db, args):
    if args.experiment is None:
        for exp in db.get_experiments():
            if args.long:
                print_exp(exp)
                print()
            else:
                print(exp.name)
    else:
        exp = db.get_experiment(args.experiment)
        for job in exp.all_jobs():
            if args.long:
                print_job(job)
                print()
            else:
                print(job.job_id)

def setup_push(subparsers):
    parser = subparsers.add_parser('push', help='Manually add a job to an existing experiment.')
    parser.set_defaults(func=cmd_push)
    parser.add_argument('experiment', help='Name of the experiment for the job.')
    parser.add_argument('-s', '--status', choices=(schedy.JOB_QUEUED, schedy.JOB_RUNNING, schedy.JOB_DONE, schedy.JOB_CRASHED), help='Status of the job.')
    parser.add_argument('-q', '--quality', type=float, help='Quality of the solution found by the job.')
    parser.add_argument('-r', '--results', nargs='+', help='Optional results for the job. Each result must be provided as a pair: name value. value must be a valid JSON value. For example: -r accuracy 0.9 loss_history \'[0.9, 0.8, 0.7]\'')
    parser.add_argument('-p', '--hyperparameters', nargs='+', required=True, help='Hyperparameters for the job. Each hyperparameter must be provided as a pair: name value. value must be a valid JSON value. For example: -p learning_rate 0.01 num_layers 3 size_layers \'[512, 1024, 512]\'')
    parser.set_defaults(parser=parser)

def cmd_push(db, args):
    kwargs = dict()
    # Status, quality
    if args.status is not None:
        kwargs['status'] = args.status
    if args.quality is not None:
        kwargs['quality'] = args.quality
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
    args = parser.parse_args()
    db = schedy.SchedyDB(config_path=args.config)
    args.func(db, args)

def print_exp(exp):
    print('Name: {}'.format(exp.name))
    print('Status: {}'.format(exp.status))
    print('Scheduler: {}'.format(exp.SCHEDULER_NAME))
    if isinstance(exp, schedy.RandomSearch):
        print('Distributions:')
        for name, dist in exp.distributions.items():
            print(' - {}: {} ({})'.format(name, dist.FUNC_NAME, json.dumps(dist.args())))

def print_job(job):
    print('Id: {}'.format(job.job_id))
    print('Status: {}'.format(job.status))
    print('Quality: {}'.format(job.quality))
    print('Hyperparameters:')
    for name, value in job.hyperparameters.items():
        print(' - {}: {}'.format(name, json.dumps(value)))
    if job.results is not None and len(job.results) > 0:
        print('Results:')
        for name, value in job.results.items():
            print(' - {}: {}'.format(name, json.dumps(value)))

if __name__ == '__main__':
    main()
