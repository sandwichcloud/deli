from deli.menu.cli.app import MetadataApplication
from deli.menu.cli.commands.run import RunMetadata


def main():
    app = MetadataApplication()
    RunMetadata().register(app)
    app.run()
