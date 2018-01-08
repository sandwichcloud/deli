from typing import Dict

from simple_settings import settings

from deli.counter.auth.driver import AuthDriver
from deli.counter.auth.drivers.database.database import Database
from deli.counter.auth.drivers.database.router import DatabaseAuthRouter
from deli.http.router import Router


class DatabaseAuthDriver(AuthDriver):

    def __init__(self):
        super().__init__("database")
        self.database = Database(settings.DATABASE_DRIVER, settings.DATABASE_HOST, settings.DATABASE_PORT,
                                 settings.DATABASE_USERNAME, settings.DATABASE_PASSWORD, settings.DATABASE_DB,
                                 settings.DATABASE_POOL_SIZE)
        self.database.connect()

    def discover_options(self) -> Dict:
        return {}

    def auth_router(self) -> Router:
        return DatabaseAuthRouter(self)
