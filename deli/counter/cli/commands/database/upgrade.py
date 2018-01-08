from clify.command import Command


class UpgradeCommand(Command):
    def __init__(self):
        super().__init__('upgrade', 'Upgrade the database to a later version')

    def setup_arguments(self, parser):
        parser.add_argument("-r", "--revision", help="The revision to upgrade to", default="head", type=str)

    def setup(self, args):
        return self.parent.setup(args)

    def run(self, args) -> int:
        self.parent.database.upgrade(args.revision)
        return 0
