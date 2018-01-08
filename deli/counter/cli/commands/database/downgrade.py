from clify.command import Command


class DowngradeCommand(Command):
    def __init__(self):
        super().__init__('downgrade', 'Downgrade the database to a earlier version')

    def setup_arguments(self, parser):
        parser.add_argument("-r", "--revision", help="The revision to downgrade to", type=str, required=True)

    def setup(self, args):
        return self.parent.setup(args)

    def run(self, args) -> int:
        self.parent.database.downgrade(args.revision)
        return 0
