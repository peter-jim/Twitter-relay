import os
import pathlib

import dotenv
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

dotenv.load_dotenv(dotenv_path=pathlib.Path.home() / '.twitter_relay' / '.env')

class Config:
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SCHEDULER_JOBSTORES = {
        'default': SQLAlchemyJobStore(url=SQLALCHEMY_DATABASE_URI)
    }
