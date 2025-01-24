import logging
import pathlib
import dotenv
from flask import Flask
from .config import Config
from .extensions import db, scheduler
from flaskr import routes


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.logger.setLevel(logging.INFO)
    # from concurrent.futures import ThreadPoolExecutor
    # app.extensions["executor"] = ThreadPoolExecutor(max_workers=10)
    # 初始化扩展
    db.init_app(app)
    scheduler.init_app(app)
    scheduler.start()
    # 注册蓝图
    app.register_blueprint(routes.bp)

    return app
