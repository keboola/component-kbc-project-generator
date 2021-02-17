'''
Template Component main class.

'''

import csv
import json
import logging
import os
import sys
from typing import List

import requests
from kbc.env_handler import KBCEnvHandler

# configuration variables
KEY_API_TOKEN = '#api_token'
KEY_ORG_ID = 'org_id'
KEY_PROJECT_TYPE = 'project_type'
KEY_REGION = 'aws_region'
KEY_MODE = 'mode'

# #### Keep for debug
KEY_DEBUG = 'debug'

MANDATORY_PARS = [KEY_API_TOKEN, KEY_REGION, KEY_ORG_ID, KEY_PROJECT_TYPE]
MANDATORY_IMAGE_PARS = []

APP_VERSION = '0.0.1'


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

        # default
        self.url_suffixes = {"US": ".keboola.com",
                             "EU": ".eu-central-1.keboola.com",
                             "AZURE-EU": ".north-europe.azure.keboola.com"}

        self.url_suffixes = {**self.url_suffixes, **self.image_params}

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
            writer = csv.DictWriter(out_file, fieldnames=['email', 'project_id', 'features'], lineterminator='\n')
            writer.writeheader()

            for row in reader:

                try:
                    mode = params.get(KEY_MODE, 'CREATE')
                    if mode == 'CREATE':
                        logging.info(f"Generating project {row['name']}, for email {row['email']}")
                        p = self._generate_project(row)

                    if mode == 'INVITE':
                        p = self._invite_users_to_project(row)

                    # log
                    writer.writerow({"email": row['email'],
                                     "project_id": p['id'],
                                     "features": row.get('features', [])})
                except Exception as e:
                    logging.warning(f'Project creation failed: {e}')
                    continue

        self.configuration.write_table_manifest(out_file_path, primary_key=["email"], incremental=True)
        logging.info('Finished!')

    def _generate_project(self, row: dict):
        p = self.create_new_project(self.cfg_params[KEY_API_TOKEN], row['name'],
                                    organisation=self.cfg_params[KEY_ORG_ID],
                                    region=self.cfg_params[KEY_REGION], p_type=self.cfg_params[KEY_PROJECT_TYPE])
        logging.info(f"Project ID {p['id']} created.")

        if row.get('features', []):
            logging.info(f'Adding project features {row["features"]}')
            self.add_features(self.cfg_params[KEY_API_TOKEN], p['id'],
                              self.comma_separated_values_to_list(row['features']),
                              region=self.cfg_params[KEY_REGION])
        if row.get('storage_backend'):
            logging.info(f'Assigning project storage backend ID {row["storage_backend"]}')
            self.assign_storage_backend_to_project(self.cfg_params[KEY_API_TOKEN], p['id'],
                                                   int(row['storage_backend']),
                                                   region=self.cfg_params[KEY_REGION])
        return p

    def _invite_users_to_project(self, row):
        if not row.get('project_id'):
            raise ValueError("The input table must contain project_id column in the INVITE mode!")
        emails = row['email']
        for email in emails.split(';'):
            if '<' in email and '>' in email:
                email = email[email.find("<") + 1:email.find(">")]
            if email:
                self.invite_user_to_project(self.cfg_params[KEY_API_TOKEN], row['project_id'], email,
                                            region=self.cfg_params[KEY_REGION])
            else:
                logging.warning('Empty email!')

        p = dict()
        p['id'] = row['project_id']
        return p

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
            f'https://connection{self.url_suffixes[region]}/manage/organizations/' + str(organisation) + '/projects',
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

        logging.debug(f"Payload: {json.dumps(data)}")
        response = requests.post(
            f'https://connection{self.url_suffixes[region]}/manage/projects/' + str(project_id) + '/users',
            data=json.dumps(data),
            headers=headers)

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise e
        else:
            return True

    def add_features(self, token: str, project_id: str, features: List[str], region):
        for f in features:
            self.add_feature(token, project_id, f, region)

    def add_feature(self, token: str, project_id: str, feature: str, region):
        headers = {
            'Content-Type': 'text/plain',
            'X-KBC-ManageApiToken': token
        }
        data = {
            "feature": feature
        }
        response = requests.post(
            f'https://connection{self.url_suffixes[region]}/manage/projects/' + str(project_id) + '/features',
            data=json.dumps(data),
            headers=headers)

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise e
        else:
            return True

    def assign_storage_backend_to_project(self, token: str, project_id: str, backend_id: int, region):
        headers = {
            'Content-Type': 'text/plain',
            'X-KBC-ManageApiToken': token
        }
        data = {
            "storageBackendId": backend_id
        }
        response = requests.post(
            f'https://connection{self.url_suffixes[region]}/manage/projects/' + str(project_id) + '/storage-backend',
            data=json.dumps(data),
            headers=headers)

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise e
        else:
            return True

    def comma_separated_values_to_list(self, param):
        cols = []
        if param:
            cols = [p.strip() for p in param.split(",")]
        return cols


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
