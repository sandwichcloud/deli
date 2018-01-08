import secrets

from clify.command import Command

from deli.counter.auth.drivers.database.models.user import User, UserRole


class GenAdminCommand(Command):
    def __init__(self):
        super().__init__('gen-admin', 'Creates an admin account in the builtin auth driver')

    def setup_arguments(self, parser):
        pass

    def setup(self, args):
        return self.parent.setup(args)

    def run(self, args) -> int:
        with self.parent.database.session() as session:
            user = session.query(User).first()
            if user is not None:
                self.logger.error("Users already exist, cannot create admin account.")
                return 1

            password = secrets.token_urlsafe()

            user = User()
            user.username = 'admin'
            user.password = password
            session.add(user)

            user_role_admin = UserRole()
            user_role_admin.role = 'admin'
            session.add(user_role_admin)

            user.roles.append(user_role_admin)

            session.commit()
            session.refresh(user)

            self.logger.info("Created an admin account with the password of " + password)
        return 0
