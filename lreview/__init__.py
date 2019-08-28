import os
import click
from flask import Flask, request
from flask_uploads import configure_uploads, patch_request_class

from lreview.setting import config
from lreview.extensions import db, login_manager, migrate, mail, photos
from lreview.apis.v1 import api_v1
from lreview.apis.v1.errors import api_abort


# when use [flask run], it will automatically invoke the function named create_app() / make_app()
def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')

    app = Flask('lreview')
    app.config.from_object(config[config_name])

    register_extensions(app)
    register_blueprints(app)
    register_errors(app)
    register_shell_context(app)
    register_template_context(app)
    return app


def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    # upload config
    configure_uploads(app, photos)
    patch_request_class(app)  # set maximum file size, default is 16MB


def register_blueprints(app):
    app.register_blueprint(api_v1, url_prefix='/api/v1')


def register_errors(app):
    # bad request / invalid hostname
    @app.errorhandler(400)
    def bad_request(e):
        return api_abort(400, message='Bad request XD.')

    # server error
    @app.errorhandler(500)
    def internal_server_error(e):
        return api_abort(400, message='Server error.')


# when use [flask shell], it will invoke the function and register the items
def register_shell_context(app):
    @app.shell_context_processor
    def make_shell_context():
        from lreview.models import User, Post, Image
        return dict(db=db, User=User, Post=Post, Image=Image)


def register_template_context(app):
    @app.context_processor
    def make_template_context():
        from lreview.models import User
        user = User.query.first()
        return dict(user=user)
