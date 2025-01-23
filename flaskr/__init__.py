from flask import Flask
from .config import Config
from .extensions import db, scheduler
from flaskr import routes


# scheduler
# from .routes import register_routes

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 初始化扩展
    db.init_app(app)
    scheduler.init_app(app)
    scheduler.start()
    # 注册蓝图
    app.register_blueprint(routes.bp)

    return app
