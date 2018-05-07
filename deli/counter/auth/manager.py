import importlib
import logging

from simple_settings import settings

from deli.counter.auth.driver import AuthDriver

DRIVERS = {}


def load_drivers():
    logger = logging.getLogger("%s.%s" % (load_drivers.__module__, load_drivers.__name__))
    for driver_string in settings.AUTH_DRIVERS:
        if ':' not in driver_string:
            raise ValueError("AUTH_DRIVER does not contain a module and class. "
                             "Must be in the following format: 'my.module:MyClass'")

        auth_module, auth_class, *_ = driver_string.split(":")
        try:
            auth_module = importlib.import_module(auth_module)
        except ImportError:
            logger.exception("Could not import auth driver's module: " + auth_module)
            raise
        try:
            driver_klass = getattr(auth_module, auth_class)
        except AttributeError:
            logger.exception("Could not get driver's module class: " + auth_class)
            raise

        if not issubclass(driver_klass, AuthDriver):
            raise ValueError("AUTH_DRIVER class is not a subclass of '" + AuthDriver.__module__ + ".AuthDriver'")

        driver: AuthDriver = driver_klass()
        DRIVERS[driver.name] = driver

    if len(DRIVERS) == 0:
        raise ValueError("No auth drivers loaded")
