from deli.manager.cli.app import ManagerApplication
from deli.manager.cli.commands.run import RunManager


def main():
    app = ManagerApplication()
    RunManager().register(app)
    app.run()
