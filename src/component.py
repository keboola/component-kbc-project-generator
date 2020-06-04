'''
Template Component main class.

'''

import csv
import json
import logging
import os
import sys

import requests
from kbc.env_handler import KBCEnvHandler

# configuration variables
KEY_API_TOKEN = '#api_token'
KEY_ORG_ID = 'org_id'
KEY_PROJECT_TYPE = 'project_type'
KEY_REGION = 'aws_region'

# #### Keep for debug
KEY_DEBUG = 'debug'

MANDATORY_PARS = [KEY_API_TOKEN, KEY_REGION, KEY_ORG_ID, KEY_PROJECT_TYPE]
MANDATORY_IMAGE_PARS = []

APP_VERSION = '0.0.1'

URL_SUFFIXES = {"US": ".keboola.com",
                "EU": ".eu-central-1.keboola.com"}


class Component(KBCEnvHandler):

    def __init__(self, debug=False):
        KBCEnvHandler.__init__(self, MANDATORY_PARS, log_level=logging.DEBUG if debug else logging.INFO)
        # override debug from config
        if self.cfg_params.get(KEY_DEBUG):
            debug = True
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
        logging.info('Running version %s', APP_VERSION)
        logging.info('Loading configuration...')

        try:
            self.validate_config(MANDATORY_PARS)
        except ValueError as e:
            logging.exception(e)
            exit(1)

    def run(self):
        '''
        Main execution code
        '''
        params = self.cfg_params  # noqa
        users_paths = os.path.join(self.tables_in_path, 'users.csv')
        out_file_path = os.path.join(self.tables_out_path, 'user_projects.csv')
        if not os.path.exists(users_paths):
            logging.exception('The table users.csv must be on input!')

        with open(users_paths, mode='rt', encoding='utf-8') as in_file, open(out_file_path, mode='w+',
                                                                             encoding='utf-8') as out_file:
            reader = csv.DictReader(in_file, lineterminator='\n')
            writer = csv.DictWriter(out_file, fieldnames=['email', 'project_id'], lineterminator='\n')
            writer.writeheader()

            for row in reader:
                logging.info(f"Generating project {row['name']}, for email {row['email']}")
                p = self.create_new_project(params[KEY_API_TOKEN], row['name'], organisation=params[KEY_ORG_ID],
                                            region=params[KEY_REGION], p_type=params[KEY_PROJECT_TYPE])
                logging.info(f"Project ID {p['id']} created.")
                logging.info(f"Inviting user {row['email']}")
                self.invite_user_to_project(params[KEY_API_TOKEN], p['id'], row['email'])
                writer.writerow({"email": row['email'],
                                 "project_id": p['id']})

            logging.info('Finished!')

    def create_new_project(self, storage_token, name, organisation, p_type='poc6months', region='EU',
                           defaultBackend='snowflake'):
        headers = {
            'Content-Type': 'application/json',
            'X-KBC-ManageApiToken': storage_token,
        }

        data = {
            "name": name,
            "type": p_type,
            "defaultBackend": defaultBackend
        }

        response = requests.post(
            f'https://connection{URL_SUFFIXES[region]}/manage/organizations/' + str(organisation) + '/projects',
            headers=headers, data=json.dumps(data))
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise e
        else:
            return response.json()

    def invite_user_to_project(self, token, project_id, email, region='US'):
        headers = {
            'Content-Type': 'text/plain',
            'X-KBC-ManageApiToken': token
        }
        data = {
            "email": email
        }
        response = requests.post(
            f'https://connection.{URL_SUFFIXES[region]}/manage/projects/' + str(project_id) + '/users',
            data=json.dumps(data),
            headers=headers)

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise e
        else:
            return True


"""
        Main entrypoint
"""
if __name__ == "__main__":
    if len(sys.argv) > 1:
        debug_arg = sys.argv[1]
    else:
        debug_arg = False
    try:
        comp = Component(debug_arg)
        comp.run()
    except Exception as exc:
        logging.exception(exc)
        exit(1)
