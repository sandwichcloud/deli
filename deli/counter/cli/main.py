import os


def main():
    os.environ['CLI'] = 'true'
    os.environ['settings'] = 'deli.counter.settings'
    from deli.counter.cli.app import CounterApplication

    app = CounterApplication()
    app.run()
