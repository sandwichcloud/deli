from clify.command import Command


class RevisionCommand(Command):
    def __init__(self):
        super().__init__('revision', 'Create a new revision file. This should only be used in development.')

    def setup_arguments(self, parser):
        parser.add_argument("message", nargs='+', help="The message to give the revision", type=str)

    def setup(self, args):
        return self.parent.setup(args)

    def run(self, args) -> int:
        message = ' '.join(args.message)

        self.logger.info("Creating a revision with the message " + message + "\n")

        self.parent.database.revision(message)
        return 0
