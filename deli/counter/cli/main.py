import os

from deli.counter.cli.commands.database.database import DatabaseCommand


def main():
    os.environ['CLI'] = 'true'
    os.environ['settings'] = 'deli.counter.settings'
    from deli.counter.cli.app import CounterApplication

    app = CounterApplication()
    app.register_command(DatabaseCommand())
    app.run()
