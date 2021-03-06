# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, render_template, request, session, g
from tinydb import TinyDB
from tinydb.storages import MemoryStorage


# TODO: rename/reorg blueprints for consistency
from .blueprints.api.api import api_blueprint
from .blueprints.admin.views import admin_blueprint
from .blueprints.developer.views import developer_blueprint
from .blueprints.portfolio.views import portfolio_blueprint
from .blueprints.events import views
from .logs import configure_logging
from .util import init_db, get_help_markdown

app = Flask(__name__)
app.secret_key = app.config['SECRET_KEY']
configure_logging()

app.static_folder = 'static'
app.add_url_rule('/static/<path:filename>',
                 endpoint='static',
                 subdomain='<tenant>',
                 view_func=app.send_static_file)

if app.config['ENV'] == 'production':  # reads from FLASK_ENV env variable
    app.config.from_object('okta_multidemo.config.ProductionConfig')
    # from .config import UdpConfig
    # import pdb;pdb.set_trace()
    # app.config.from_object(UdpConfig())
    # Talisman(app, content_security_policy=None)
else:
    app.config.from_object('okta_multidemo.config.DevelopmentConfig')

# TODO: need to import after app.config takes place -- is this ok?
from .okta import okta_blueprint, okta_admin_blueprint, okta_o4o_blueprint  # noqa
from . import views  # noqa


@app.before_request
def before_request():
    global app

    # NOTE: normally excluding static assets would be handled by the webserver
    if request.path.startswith('/static') or request.path.startswith('/api'):
        return

    # init db for subdomain
    subdomain = urlparse(request.url).hostname.split('.')[0]
    if subdomain not in session:
        session['subdomain'] = subdomain
    if subdomain not in app.config['DB_CONNS']:
        # db = TinyDB('/tmp/{}.json'.format(subdomain))
        db = TinyDB(storage=MemoryStorage)
        app.config['DB_CONNS'][subdomain] = db
        init_db(db, app.config['ENV'])

    # handle help URLs
    if request.path.endswith('/'):
        path = request.path + 'index'
    else:
        path = request.path[1:]
    try:
        g.help = get_help_markdown(path, session, request)

    except FileNotFoundError:
        logging.warning('No help file found for {} view'.format(path))


def page_not_found(e):
    return render_template('404.html'), 404


def server_error(e):
    return render_template('500.html'), 500


def unauthorized(e):
    return render_template('401.html'), 401


app.register_blueprint(okta_blueprint, url_prefix='/login')
app.register_blueprint(okta_admin_blueprint, url_prefix='/login')
app.register_blueprint(okta_o4o_blueprint, url_prefix='/login')
blueprints = [
    api_blueprint,
    admin_blueprint,
]
if app.config['FF_DEVELOPER']:
    blueprints.append(developer_blueprint)
if app.config['FF_PORTFOLIO']:
    blueprints.append(portfolio_blueprint)
# TODO: ^^^ refactor as additional FF's are added
for blueprint in blueprints:
    app.register_blueprint(blueprint)

app.register_error_handler(404, page_not_found)
app.register_error_handler(500, server_error)
app.register_error_handler(401, unauthorized)
