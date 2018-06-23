from deli.menu.cli.app import MetadataApplication
from deli.menu.cli.commands.run import RunMetadataMenu


def main():
    app = MetadataApplication()
    RunMetadataMenu().register(app)
    app.run()
