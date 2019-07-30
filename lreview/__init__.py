import os
import click
from flask import Flask, request

from lreview.setting import config
from lreview.extensions import db, login_manager, migrate
from lreview.apis.v1 import api_v1

# from lreview.models import Admin, Category

# when use [flask run], it will automatically invoke the function named create_app() / make_app()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'development')

    app = Flask('lreview')
    app.config.from_object(config[config_name])

    register_logging(app)
    register_extensions(app)
    register_blueprints(app)
    register_errors(app)
    register_shell_context(app)
    register_template_context(app)
    return app


def register_logging(app):
    pass


def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)


def register_blueprints(app):
    app.register_blueprint(api_v1, url_prefix='/api/v1')


def register_errors(app):
    # bad request / invalid hostname
    @app.errorhandler(400)
    def bad_request(e):
        # return render_template('errors/400.html'), 400
        pass

    # server error
    @app.errorhandler(500)
    def internal_server_error(e):
        # return render_template('errors/500.html'), 500
        pass


# when use [flask shell], it will invoke the function and register the items


def register_shell_context(app):
    @app.shell_context_processor
    def make_shell_context():
        from lreview.models import User, Post
        return dict(db=db, User=User, Post=Post)


def register_template_context(app):
    @app.context_processor
    def make_template_context():
        user = User.query.first()
        categories = Category.query.order_by(Category.name).all()
        return dict(user=user, categories=categories)
