#!/usr/bin/env python3

import argparse
from datetime import date, timedelta
import logging
import os
import time

from prometheus_client import start_http_server, Summary
from prometheus_client.core import GaugeMetricFamily, REGISTRY
from float_api import FloatAPI, UnexpectedStatusCode, DataValidationError
import yaml

# Create a metric to track time spent and requests made.
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')

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


class FloatCollector(object):

    def __init__(self, float_api, report_periods):

      # The Float API object
      self.api = float_api
      # List of periods to report for
      self.report_periods = report_periods

    @REQUEST_TIME.time()
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
        try:
            for a_id, a_name in ACCOUNT_TYPES.items():
              g = GaugeMetricFamily(
                  'float_accounts',
                  'Number of accounts',
                  labels=['account_type']
                  )
              g.add_metric(
                  [a_name],
                  len([a for a in float_accounts if a['account_type'] == a_id])
                  )
              yield g
        except Exception as e:
            logging.error("Could not build build metric 'float_accounts': {}".format(e))


        # Number of clients
        try:
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
        except Exception as e:
            logging.error("Could not build build metric 'float_clients': {}".format(e))


        # Number of people
        try:
            for e_type in [1,2,3]:
                g = GaugeMetricFamily(
                    'float_people',
                    'Number of people',
                    labels=['people_type']
                    )
                g.add_metric(
                    [str(e_type)],
                    len([p for p in float_people if p['people_type_id'] == e_type]),
                    )
                yield g
        except Exception as e:
            logging.error("Could not build build metric 'float_people': {}".format(e))


        # Number of projects
        try:
            for is_active in [0, 1]:
                g = GaugeMetricFamily(
                    'float_projects',
                    'Number of projects',
                    labels=['active']
                    )
                g.add_metric(
                    [str(is_active)],
                    len([p for p in float_projects if p['active'] == is_active]),
                    )
                yield g
        except Exception as e:
            logging.error("Could not build build metric 'float_projects': {}".format(e))


        # Budget sum
        try:
            for budget_type in [1,2,3]:
                g = GaugeMetricFamily(
                    'float_projects_budget_sum',
                    'The sum of project budgets',
                    labels=['type']
                    )
                # List of budgets as floats
                budgets = [float(p['budget_total']) for p in float_projects if p['budget_type'] == budget_type]
                g.add_metric(
                    [str(budget_type)],
                    sum(budgets),
                    )
                yield g
        except Exception as e:
            logging.error("Could not build build metric 'float_projects_budget_sum': {}".format(e))


        # Number of projects with budget
        try:
            for budget_type in [1,2,3]:
                g = GaugeMetricFamily(
                    'float_projects_with_budget',
                    'Number of projects with budgets',
                    labels=['type']
                    )
                g.add_metric(
                    [str(budget_type)],
                    len([ p for p in float_projects if p['budget_type'] == budget_type])
                    )
                yield g
        except Exception as e:
            logging.error("Could not build build metric 'float_tasks': {}".format(e))


        # Number of billable projects
        try:
            for is_active in [0, 1]:
                g = GaugeMetricFamily(
                    'float_projects_billable',
                    'Number of billable projects',
                    labels=['active']
                    )
                g.add_metric(
                    [str(is_active)],
                    len([p for p in float_projects if p['active'] == is_active and p['non_billable'] == 0]),
                    )
                yield g
        except Exception as e:
            logging.error("Could not build build metric 'float_projects_billable': {}".format(e))


        # Number of people in departments
        try:
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
        except Exception as e:
            logging.error("Could not build build metric 'float_department_members': {}".format(e))


        # Department_id name mapping
        try:
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
        except Exception as e:
            logging.error("Could not build build metric 'float_department_id': {}".format(e))


        ###################
        # TIME BASED DATA #
        ###################

        # Loop through the periods to report for
        #for period in REPORT_PERIODS:
        for period in self.report_periods:
          
          # Get the data from Float
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
          try:
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
          except Exception as e:
              logging.error("{}: {} when building metric 'float_tasks'".format(type(e).__name__, e))


          # Sum of task hours
          try:
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
          except Exception as e:
              logging.error("Could not build build metric 'float_tasks_hours': {}".format(e))


          # Number of people with tasks
          try:
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
          except Exception as e:
              logging.error("Could not build build metric 'float_tasks_people': {}".format(e))


          # People report
          
          # Create metrics for these fields
          metrics = [
            'overtime',
            'billable',
            'nonBillable',
            'capacity',
            'scheduled',
            'unscheduled',
            'timeoff'
            ]
          try:
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
          except Exception as e:
              logging.error("Could not build build metric 'float_people_report_x_hours': {}".format(e))

          # Project report clients
          try:
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
          except Exception as e:
              logging.error("Could not build build metric 'float_project_report_clients': {}".format(e))

          # Project report projects
          try:
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
          except Exception as e:
              logging.error("Could not build build metric 'float_project_report_projects': {}".format(e))

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
    default_conf_file = '/etc/float_exporter.yml'

    # Parser object
    parser = argparse.ArgumentParser(
        description=('Exports data from Float to be consumed by '
          'Prometheus. Can be configured through config file '
          '(Lowest priority), environment variables and CLI '
          '(Highest priority).'
          )
    )

    # Float access token. Default to env variable FLOAT_ACCESS_TOKEN
    parser.add_argument(
        '--access-token',
        metavar='FLOAT_ACCESS_TOKEN',
        required=False,
        help=('Access token for accessing the Float API. '
          'Defaults to environment variable FLOAT_ACCESS_TOKEN'),
        default=None
    )

    parser.add_argument(
        '--email',
        metavar='FLOAT_EMAIL',
        required=False,
        help=('Email to supply as part of User-Agent. '
          'Defaults to environment variable FLOAT_EMAIL'),
        default=None
    )

    parser.add_argument(
        '--user-agent',
        metavar='FLOAT_USER_AGENT',
        required=False,
        help=('String to report as User-Agent when getting data from Float. '
          'Defaults to environment variable FLOAT_USER_AGENT'),
        default=None
    )

    # Port to listen on
    parser.add_argument(
        '--port',
        metavar=default_port,
        required=False,
        type=int,
        help='Port to recieve request on.',
        default=None
    )

    # Location of config file
    parser.add_argument(
        '--config-file',
        metavar=default_conf_file,
        required=False,
        help='The file to read configuration from.',
        default=None
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
      #default=default_log_level,
      default=None,
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
        args_cli = parse_args()

        config = {
          'log_file': None,
          'log_level': 'INFO',
          'disable_log_stdout': False,
          'email': None,
          'config_file': '/etc/float_exporter.yml',
          'user_agent': 'Prometheus float_exporter',
          'access_token': None,
          'report_days': [7, 14],
          'port': 9709
          }


        # Update config_file if supplied by CLI
        if args_cli.config_file:
          config['config_file'] = args_cli.config_file

        # Exit with error if specified config file does not exist
        if not os.path.isfile(config['config_file']):
            m = ("Error: Config file {} does not exist.".
              format(config['config_file']))
            print(m)
            exit(1)

        # Overwrite config with values in config file
        args_file = parse_config(config['config_file'])
        for a_name, a_value in args_file.items():
          if a_value and a_name in config.keys():
            config[a_name] = a_value

        # Overwrite config with values form env variables.
        for a_name in config.keys():
          config[a_name] = os.environ.get(
            'FLOAT_' + a_name.upper(),
            config[a_name]
            )

        # Overwrite config with values from CLI
        for a_name, a_value in args_cli.__dict__.items():
          if a_value and a_name in config.keys():
            config[a_name] = a_value

        # A list of logging handlers
        logging_handlers = []

        # Log to file if we have a log file
        if config['log_file']:
          logging_handlers.append(
            logging.FileHandler(config['log_file'])
            )

        # Log to stdout if not disabled
        if not config['disable_log_stdout']:
          logging_handlers.append(logging.StreamHandler())

        # Abort if all logging disabled by user
        if logging_handlers == []:
          print("Error: Can not run with all logging disabled.")
          exit(1)

        # Configure logging
        logging.basicConfig(
          level = eval("logging." + config['log_level']),
          format='%(asctime)s:%(levelname)s:%(message)s',
          handlers = logging_handlers
          )

        # Make sure we have an email
        if not config['email']:
          m = "No email configured."
          logging.error(m)
          print("Error:", m)
          exit(1)

        # Make sure we have an access token
        if not config['access_token']:
          m = "No access token configured"
          logging.error(m)
          print("Error:", m)
          exit(1)

        # Store dictionaries defining periods here
        report_periods = []

        # Log if no report days supplied
        if len(config['report_days']) == 0:
          logging.info("Report metrics disabled because of no report_days")

        # Add the periods to report for based on config
        for d in config['report_days']:
          # Calculate days for the period
          p = {
            'name': str(d),
            'start_date': date.today().isoformat(),
            'end_date': (date.today() + timedelta(days=d)).isoformat()
            }
          # Add the period
          report_periods.append(p)

        # Log config
        for key, value in config.items():
          if key == "access_token":
            value = "{}{}{}".format(value[0:3], "*******", value[-3:])
          logging.debug("Config {}: {}".format(key, value))

        # Instantiate Float API
        float_api = FloatAPI(
            config['access_token'],
            config['user_agent'],
            config['email']
            )

        logging.info("Starting float_exporter")

        # Instantiate collector
        REGISTRY.register(FloatCollector(float_api, report_periods))

        # Listen for scrape requests.
        start_http_server(config['port'])

        # Run forever
        while True:
          time.sleep(3600)

    except KeyboardInterrupt:
        print(" Interrupted by keyboard")
        exit(0)


if __name__ == '__main__':
    main()
