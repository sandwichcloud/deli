import os

from deli.manager.cli.commands.run import RunManager


def main():
    os.environ['settings'] = 'deli.manager.settings'
    from deli.manager.cli.app import ManagerApplication

    app = ManagerApplication()
    RunManager().register(app)
    app.run()
