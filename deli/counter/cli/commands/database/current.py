from clify.command import Command


class CurrentCommand(Command):
    def __init__(self):
        super().__init__('current', 'Display the current revision for the database')

    def setup_arguments(self, parser):
        pass

    def setup(self, args):
        return self.parent.setup(args)

    def run(self, args) -> int:
        self.logger.info("The current database revision is: " + self.parent.database.current())
        return 0
