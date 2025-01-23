import os
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore


class Config:
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "mysql+pymysql://root:wanbe2426@localhost/test_db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SCHEDULER_JOBSTORES = {
        'default': SQLAlchemyJobStore(url=SQLALCHEMY_DATABASE_URI)
    }
