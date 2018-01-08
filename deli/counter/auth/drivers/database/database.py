import logging
import os
from contextlib import contextmanager

import alembic
import alembic.command
import alembic.config
import sqlalchemy
import sqlalchemy.event
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, exc
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy_utils import force_auto_coercion

force_auto_coercion()
Base = declarative_base()


class Database(object):
    def __init__(self, driver, host, port, username, password, database, pool_size):
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))

        self.driver = driver
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.pool_size = pool_size

        self.migration_scripts_location = "deli.counter.auth.drivers.database:alembic"
        self.engine = None

    def connect(self):
        database = {
            'drivername': self.driver,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'database': self.database
        }
        if self.driver == "sqlite" or self.pool_size == -1:
            self.engine = create_engine(URL(**database), poolclass=NullPool)
        else:
            self.engine = create_engine(URL(**database), poolclass=QueuePool, pool_size=self.pool_size)

        self._add_process_guards(self.engine)
        self._add_disconnection_guards(self.engine)

    def _add_process_guards(self, engine):
        """Add multiprocessing guards.

        Forces a connection to be reconnected if it is detected
        as having been shared to a sub-process.

        """

        @sqlalchemy.event.listens_for(engine, "connect")
        def connect(dbapi_connection, connection_record):
            connection_record.info['pid'] = os.getpid()

        @sqlalchemy.event.listens_for(engine, "checkout")
        def checkout(dbapi_connection, connection_record, connection_proxy):
            pid = os.getpid()
            if connection_record.info['pid'] != pid:
                self.logger.debug(
                    "Parent process %(orig)s forked (%(newproc)s) with an open database connection, "
                    "which is being discarded and recreated." % {"newproc": pid, "orig": connection_record.info['pid']})
                connection_record.connection = connection_proxy.connection = None
                raise exc.DisconnectionError(
                    "Connection record belongs to pid %s, attempting to check out in pid %s" % (
                        connection_record.info['pid'], pid)
                )

    def _add_disconnection_guards(self, engine):
        @sqlalchemy.event.listens_for(engine.pool, "checkout")
        def ping_connection(dbapi_connection, connection_record, connection_proxy):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("SELECT 1")
            except:  # noqa: E722
                connection_proxy._pool.dispose()
                # raise DisconnectionError - pool will try
                # connecting again up to three times before raising.
                raise exc.DisconnectionError()
            cursor.close()

    @contextmanager
    def session(self):

        session = scoped_session(sessionmaker())
        session.configure(bind=self.engine)
        session = session()

        try:
            yield session
        finally:
            session.close()
            scoped_session(sessionmaker()).remove()

    def close(self):
        sessionmaker().close_all()
        self.engine.dispose()

    def alembic_config(self):
        alembic_config = alembic.config.Config()
        alembic_config.set_main_option("script_location", self.migration_scripts_location)
        alembic_config.set_main_option("sqlalchemy.url", str(self.engine.url))

        return alembic_config

    def current(self):
        """
        Display the current database revision
        """

        config = self.alembic_config()
        script = ScriptDirectory.from_config(config)

        revision = 'base'

        def display_version(rev, context):
            for rev in script.get_all_current(rev):
                nonlocal revision
                revision = rev.cmd_format(False)

            return []

        with EnvironmentContext(config, script, fn=display_version):
            script.run_env()

        return revision

    def history(self):
        """
        List the changeset scripts in chronological order.
        """
        alembic.command.history(self.alembic_config(), verbose=True)

    def upgrade(self, revision):
        """
        Upgrade the database
        """
        alembic.command.upgrade(self.alembic_config(), revision)

    def downgrade(self, revision):
        """
        Downgrade the database to a previous version

        :param revision:
        """
        alembic.command.downgrade(self.alembic_config(), revision)

    def revision(self, message):
        """
        Create a new revision file

        :param message:
        """
        alembic.command.revision(self.alembic_config(), message=message)
