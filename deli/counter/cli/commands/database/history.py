from clify.command import Command


class HistoryCommand(Command):
    def __init__(self):
        super().__init__('history', 'List the changeset scripts in chronological order')

    def setup_arguments(self, parser):
        pass

    def setup(self, args):
        return self.parent.setup(args)

    def run(self, args) -> int:
        self.parent.database.history()
        return 0
