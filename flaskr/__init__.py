import logging
from flask import Flask
from .config import Config
from .extensions import db, scheduler
from flaskr import admin, api


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.logger.setLevel(logging.INFO)

    db.init_app(app)
    scheduler.init_app(app)
    scheduler.start()
    
    app.register_blueprint(api.bp)
    app.register_blueprint(admin.bp)
    
    return app
