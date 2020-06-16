#!/usr/bin/env python3

import argparse
from datetime import date, timedelta
import logging
import os
#import random
import time

from prometheus_client import start_http_server, Summary
from prometheus_client.core import GaugeMetricFamily, HistogramMetricFamily, REGISTRY
from float_api import FloatAPI, UnexpectedStatusCode, DataValidationError
import yaml

# Create a metric to track time spent and requests made.
#REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')

# Decorate function with metric.
#@REQUEST_TIME.time()
#def process_request(t):
#    """A dummy function that takes some time."""
#    time.sleep(t)
#TEAM_NAME = "foobar team"

# Map task statuses to names
TASK_STATUSES = {
  1: 'tentative',
  2: 'confirmed',
  3: 'complete'
  }

# Map account types to names
ACCOUNT_TYPES = {
  1: 'account_owner',
  2: 'admin',
  3: 'project_manager',
  4: 'member',
  5: 'billing'
  }

REPORT_PERIODS = [
    { 'name': '7',
      'start_date': date.today().isoformat(),
      'end_date': (date.today() + timedelta(days=7)).isoformat()
    },
    { 'name': '14',
      'start_date': date.today().isoformat(),
      'end_date': (date.today() + timedelta(days=14)).isoformat()
    }
  ]

# Days relative to today to report for
REPORT_DAYS = 7

class FloatCollector(object):

    def __init__(self, float_api):

      self.api = float_api


    def collect(self):

        logging.info("Recieved request.")

        # Metric for status on getting data from Float
        float_up = GaugeMetricFamily(
            'float_up',
            'Is data beeing pulled from Float',
            labels=[]
            )

        # Get data from Float
        try:
          float_accounts = self.api.get_all_accounts()
          float_people = self.api.get_all_people()
          float_projects = self.api.get_all_projects()
          float_clients = self.api.get_all_clients()
          float_departments = self.api.get_all_departments()
        except Exception as e:
          logging.error("Exception when getting data from Float: {}"
            .format(e))
          # Report missing data and return
          float_up.add_metric([], 0)
          yield float_up
          return

        # Number of accounts
        for a_id, a_name in ACCOUNT_TYPES.items():
          g = GaugeMetricFamily(
              'float_accounts',
              'The total number of accounts',
              labels=['account_type']
              )
          g.add_metric(
              [a_name],
              len([a for a in float_accounts if a['account_type'] == a_id])
              )
          yield g


        # Number of clients
        g = GaugeMetricFamily(
            'float_clients',
            'Number of clients',
            labels=[]
            )
        g.add_metric(
            [],
            len(float_clients),
            )
        yield g


        # Number of people
        for e_type in [1,2,3]:
            g = GaugeMetricFamily(
                'float_people',
                'The number of people',
                labels=['people_type']
                )
            g.add_metric(
                [str(e_type)],
                len([p for p in float_people if p['people_type_id'] == e_type]),
                )
            yield g


        # Number of projects
        for is_active in [0, 1]:
            g = GaugeMetricFamily(
                'float_projects',
                'The number of projects',
                labels=['active']
                )
            g.add_metric(
                [str(is_active)],
                len([p for p in float_projects if p['active'] == is_active]),
                )
            yield g


        # Budget
        for budget_type in [1,2,3]:
            g = GaugeMetricFamily(
                'float_projects_budget',
                'The sum of project budgets',
                labels=['type']
                )
            d = [float(p['budget_total']) for p in float_projects if p['budget_type'] == budget_type]
            g.add_metric(
                [str(budget_type)],
                sum(d),
                )
            yield g

        # FIXME: Number of projects with budget


        # Number of billable projects
        for is_active in [0, 1]:
            g = GaugeMetricFamily(
                'float_projects_billable',
                'The number of billable projects in the team',
                labels=['active']
                )
            g.add_metric(
                [str(is_active)],
                len([p for p in float_projects if p['active'] == is_active and p['non_billable'] == 0]),
                )
            yield g


        # Number of people in departments
        for d in float_departments:
            g = GaugeMetricFamily(
                'float_department_members',
                'Number of members in department',
                labels=['department_id']
                )
            g.add_metric(
                [str(d['department_id'])],
                len([p for p in float_people if p['department'] and d['department_id'] in p['department'].values()]),
                )
            yield g


        # Department_id name mapping
        for d in float_departments:
            g = GaugeMetricFamily(
                'float_department_id',
                'ID of department',
                labels=['name']
                )
            g.add_metric(
                [d['name']],
                d['department_id'],
                )
            yield g


        ###################
        # TIME BASED DATA #
        ###################

        # Loop through the periods to report for
        for period in REPORT_PERIODS:
          
          try:
            # People reports
            float_people_reports = self.api.get_people_reports(
              start_date=period['start_date'], end_date=period['end_date'])
  
            # Project reports
            float_project_reports = self.api.get_project_reports(
              start_date=period['start_date'], end_date=period['end_date'])
  
            # Tasks
            float_tasks = self.api.get_all_tasks(
              start_date=period['start_date'], end_date=period['end_date'])
          except Exception as e:
            logging.error("Exception when getting data from Float: {}"
              .format(e))
            # Report missing data and return
            float_up.add_metric([], 0)
            yield float_up
            return


          # Number of tasks
          for p in [0, 1]:
            for s_id, s_name in TASK_STATUSES.items():
              g = GaugeMetricFamily(
                  'float_tasks',
                  'Number of tasks',
                  labels=['priority', 'status', 'days']
                  )
              g.add_metric(
                  [str(p), s_name, period['name']],
                  len([t for t in float_tasks if t['priority'] == p and t['status'] == s_id])
                  )
              yield g

          # Sum of task hours
          g = GaugeMetricFamily(
              'float_tasks_hours',
              'Sum of task hours',
              labels=['days']
              )
          g.add_metric(
              [period['name']],
              sum([ float(t['hours']) for t in float_tasks ])
              )
          yield g

          # Number of people with tasks
          g = GaugeMetricFamily(
              'float_tasks_people',
              'Number of people with tasks',
              labels=['days']
              )
          g.add_metric(
              [period['name']],
              len(set([ t['people_id'] for t in float_tasks ]))
              )
          yield g

          # People report
          metrics = [
            'overtime',
            'billable',
            'nonBillable',
            'capacity',
            'scheduled',
            'unscheduled',
            'timeoff'
            ]
          for m in metrics:
              for d_id in [d['department_id'] for d in float_departments]:
                  g = GaugeMetricFamily(
                      'float_people_report_{}_hours'.format(m.lower()),
                      'Number of {} hours'.format(m.lower()),
                      labels=['department_id', 'days']
                      )
                  g.add_metric(
                      [str(d_id), period['name']],
                      sum([ float(r[m]) for r in float_people_reports if r['department_id'] == d_id])
                      )
                  yield g

          # Project report clients
          g = GaugeMetricFamily(
              'float_project_report_clients',
              'Number of clients worked for',
              labels=['days']
              )
          g.add_metric(
              [period['name']],
              len(set([ p['client_id'] for p in float_project_reports ]))
              )
          yield g

          # Project report projects
          g = GaugeMetricFamily(
              'float_project_report_projects',
              'The number of projects worked for'.format(m),
              labels=['days']
              )
          g.add_metric(
              [period['name']],
              len(set([ p['project_id'] for p in float_project_reports ]))
              )
          yield g

          # END DATE BASED DATA


        logging.info("Done getting data from Float.")

        # Report date from Float OK. We would have
        # returned earlier if it was not
        float_up.add_metric([], 1)
        yield float_up


def parse_args():
    '''
    Parse the command line arguments
    '''

    # Defaults
    default_port = 9709
    default_log_level = 'INFO'

    # Parser object
    parser = argparse.ArgumentParser(
        description='Exports data from Float to be consumed by Prometheus'
    )

    # Float access token. Default to env variable FLOAT_ACCESS_TOKEN
    parser.add_argument(
        '--access-token',
        metavar='FLOAT_ACCESS_TOKEN',
        required=False,
        help=('Access token for accessing the Float API. '
          'Defaults to environment variable FLOAT_ACCESS_TOKEN'),
        default=os.environ.get('FLOAT_ACCESS_TOKEN', None)
    )

    parser.add_argument(
        '--email',
        metavar='FLOAT_EMAIL',
        required=False,
        help=('Email to supply as part of User-Agent. '
          'Defaults to environment variable FLOAT_EMAIL'),
        default=os.environ.get('FLOAT_EMAIL', None)
    )

    parser.add_argument(
        '--user-agent',
        metavar='FLOAT_USER_AGENT',
        required=False,
        help=('String to report as User-Agent. '
          'Defaults to environment variable FLOAT_USER_AGENT'),
        default=os.environ.get('FLOAT_USER_AGENT', None)
    )

    # Port to listen on
    parser.add_argument(
        '--port',
        metavar=default_port,
        required=False,
        type=int,
        help='Port to recieve request on.',
        default=default_port
    )

    # Location of log file
    parser.add_argument(
        '--log-file',
        metavar='',
        required=False,
        help='Location of log file. Specify to enable logging to file.',
    )

    # Log level
    parser.add_argument(
      "--log-level",
      metavar=default_log_level,
      choices=['DEBUG', 'INFO', 'WARNING', 'ALL'],
      default=default_log_level,
      help="Set log level to one of: DEBUG, INFO, WARNING, ALL."
      )

    # Disable log to stdout. Default false
    parser.add_argument(
        "--disable-log-stdout",
        # True if specified, False otherwise
        action='store_true',
        help="Specify to disable logging to stdout."
    )

    return parser.parse_args()


def parse_config(config_file):
  '''Parse content of YAML configuration file to dict'''

  # Open file stream
  stream = open(config_file, 'r')

  # Get at dictionary of the data
  config_dict = yaml.load(stream, Loader=yaml.FullLoader)

  # Close file
  stream.close()

  return config_dict


def main():
    
    try:
        # Parse the command line arguments
        args = parse_args()

        # A list of logging handlers
        logging_handlers = []

        # Handler for logging to file
        if args.log_file:
          logging_handlers.append(logging.FileHandler(args.log_file))

        # Log to stdout if not disabled
        if not args.disable_log_stdout:
          logging_handlers.append(logging.StreamHandler())

        # Abort if all logging disabled by user
        if logging_handlers == []:
          print("Error: Can not run with all logging disabled.")
          exit(1)

        # Configure logging
        logging.basicConfig(
          level = eval("logging." + args.log_level),
          format='%(asctime)s:%(levelname)s:%(message)s',
          handlers = logging_handlers
          )

        # Make sure we have an email
        if not args.email:
          raise ValueError("You must supply an email. Use environment "
            "variable FLOAT_EMAIL or flag --email")

        # Make sure we have a user agent
        if not args.user_agent:
          raise ValueError("You must supply a user agent string. "
            "Use environment variable FLOAT_USER_AGENT or flag --user-agent")

        # Make sure we have an access token
        if not args.access_token:
          raise ValueError("You must supply a Float access token. "
            "Use environment variable FLOAT_ACCESS_TOKEN or flag --access-token")

        logging.info("Starting float_exporter")

        # Instantiate Float API
        float_api = FloatAPI(
            args.access_token,
            args.user_agent,
            args.email,
            )

        # Instantiate collector
        REGISTRY.register(FloatCollector(float_api))

        # Listen for scrape requests.
        start_http_server(args.port)

        # Run forever
        while True:
          time.sleep(3600)

    except KeyboardInterrupt:
        print(" Interrupted by keyboard")
        exit(0)


if __name__ == '__main__':
    main()
