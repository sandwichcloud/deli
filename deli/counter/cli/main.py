import os

from deli.counter.cli.commands.gen_admin import GenAdmin


def main():
    os.environ['CLI'] = 'true'
    os.environ['settings'] = 'deli.counter.settings'
    from deli.counter.cli.app import CounterApplication

    app = CounterApplication()
    GenAdmin().register(app)
    app.run()
