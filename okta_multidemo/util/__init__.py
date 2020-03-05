import json
import os

from pathlib import Path

import mistune
import jwt

from simple_rest_client.api import API
from simple_rest_client.resource import Resource

from tinydb import TinyDB


def init_db(path, theme_mode, theme):
    try:
        os.remove(path)
    except OSError:
        pass
    db = TinyDB(path)
    table = db.table('items')
    path = Path(__file__).parent.absolute()
    with open(os.path.join(
            path, '..', 'conf/{}/{}/data.json'.format(theme_mode, theme)
        )) as file_:
        data = file_.read()
    items = json.loads(data)
    table.insert_multiple(items)

    table = db.table('orders')
    with open(os.path.join(
            path, '..', 'conf/orders.json'.format(theme_mode, theme)
        )) as file_:
        data = file_.read()
    items = json.loads(data)
    table.insert_multiple(items)


# NOTE: this is a simple_rest_client kludge
def get_api_default_actions(resource):
    return {
      'create': {
        'method': 'POST',
        'url': resource
      },
      'destroy': {
        'method': 'DELETE',
        'url': '%s/{}' % resource
      },
      'list': {
        'method': 'GET',
        'url': resource
      },
      'partial_update': {
        'method': 'PATCH',
        'url': '%s/{}' % resource
      },
      'retrieve': {
        'method': 'GET',
        'url': '%s/{}' % resource
      },
      'update': {
        'method': 'PUT',
        'url': '%s/{}' % resource
      }
    }


class APIClient(object):
    def __init__(self, api_url, access_token):
        self.api = API(
            api_root_url=api_url,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': 'Bearer {}'.format(access_token),
            },
            timeout=10,
            json_encode_body=True,
        )


class OktaAPIClient(object):
    def __init__(self, org_url, api_key):
        self.api = API(
            api_root_url='{}/api/v1'.format(org_url),
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': 'SSWS {}'.format(api_key),
            },
            timeout=10,
            json_encode_body=True,
        )


class UserFactorResource(Resource):
    actions = {
        'get': {'method': 'GET', 'url': 'users/{}/factors'},
        'issue': {'method': 'POST', 'url': 'users/{}/factors/{}/verify'},
        'verify': {'method': 'GET', 'url': 'users/{}/factors/{}/transactions/{}'}
    }
    actions.update(get_api_default_actions('factors'))


def decode_token(token):
    return jwt.decode(token, verify=False)


def get_help_markdown(view_name, session):
    logged_in_ext = ''
    if session.get('username'):
        logged_in_ext = '-logged-in'
    path = Path(__file__).parent.absolute()
    if view_name.endswith('/'):
        view_name = view_name + 'index'
    try:
        with open(os.path.join(path, '..', 'help/{}{}.md'.format(view_name, logged_in_ext))) as file_:
            data = file_.read()
    except:  # TODO: specify exception class
        with open(os.path.join(path, '..', 'help/{}.md'.format(view_name))) as file_:
            data = file_.read()
    return mistune.markdown(data)
