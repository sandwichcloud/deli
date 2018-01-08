import arrow
import cherrypy

from deli.counter.auth.drivers.database.models.user import User, UserRole
from deli.counter.auth.validation_models.database import RequestDatabaseLogin, RequestDatabaseCreateUser, \
    ResponseDatabaseUser, ParamsDatabaseUser, ParamsListDatabaseUser, RequestDatabaseChangePassword, \
    RequestDatabaseUserRole
from deli.counter.http.mounts.root.routes.v1.auth.validation_models.tokens import ResponseOAuthToken
from deli.http.request_methods import RequestMethods
from deli.http.route import Route
from deli.http.router import Router


class DatabaseAuthRouter(Router):

    def __init__(self, driver):
        super().__init__(uri_base='database')
        self.driver = driver

    @Route(route='login', methods=[RequestMethods.POST])
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.model_in(cls=RequestDatabaseLogin)
    @cherrypy.tools.model_out(cls=ResponseOAuthToken)
    def login(self):
        request: RequestDatabaseLogin = cherrypy.request.model
        with self.driver.database.session() as session:
            user: User = session.query(User).filter(User.username == request.username).first()
            if user is None or user.password != request.password:
                raise cherrypy.HTTPError(403, "Invalid username or password")

            expiry = arrow.now().shift(days=+1)
            token = self.driver.generate_user_token(expiry, user.username, [role.role for role in user.roles])
            session.commit()

            response = ResponseOAuthToken()
            response.access_token = token
            response.expiry = expiry
            return response

    @Route(route='users', methods=[RequestMethods.POST])
    @cherrypy.tools.enforce_policy(policy_name="database:users:create")
    @cherrypy.tools.model_in(cls=RequestDatabaseCreateUser)
    @cherrypy.tools.model_out(cls=ResponseDatabaseUser)
    def create_user(self):
        request: RequestDatabaseCreateUser = cherrypy.request.model
        with self.driver.database.session() as session:
            user = User()
            user.username = request.username
            user.password = request.password

            session.add(user)
            session.commit(user)
            session.refresh(user)

        return ResponseDatabaseUser.from_database(user)

    @Route(route='users/{user_id}')
    @cherrypy.tools.model_params(cls=ParamsDatabaseUser)
    @cherrypy.tools.enforce_policy(policy_name="database:users:get")
    @cherrypy.tools.model_out(cls=ResponseDatabaseUser)
    def get_user(self, user_id):

        with self.driver.database.session() as session:
            user: User = session.query(User).filter(User.id == user_id).first()

            if user is None:
                raise cherrypy.HTTPError(404, "The resource could not be found.")

        return ResponseDatabaseUser.from_database(user)

    @Route(route='users')
    @cherrypy.tools.model_params(cls=ParamsListDatabaseUser)
    @cherrypy.tools.enforce_policy(policy_name="database:users:list")
    @cherrypy.tools.model_out_pagination(cls=ResponseDatabaseUser)
    def list_users(self, limit, marker):
        return self.paginate(User, ResponseDatabaseUser, limit, marker)

    @Route(route='users/{user_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsDatabaseUser)
    @cherrypy.tools.enforce_policy(policy_name="database:users:delete")
    def delete_user(self, user_id):
        cherrypy.response.status = 204
        with self.driver.database.session() as session:
            user: User = session.query(User).filter(User.id == user_id).first()

            if user is None:
                raise cherrypy.HTTPError(404, "The resource could not be found.")

            if user.username == "admin":
                raise cherrypy.HTTPError(400, "Cannot delete admin user.")

            session.delete(user)
            session.commit()

    @Route(route='users', methods=[RequestMethods.PATCH])
    @cherrypy.tools.model_in(cls=RequestDatabaseChangePassword)
    def change_password_self(self):
        cherrypy.response.status = 204
        request: RequestDatabaseChangePassword = cherrypy.request.model
        with self.driver.database.session() as session:
            if cherrypy.request.user.driver != self.driver.name:
                raise cherrypy.HTTPError(400, "Token is not using 'Database' authentication.")

            user: User = session.query(User).filter(
                User.username == cherrypy.request.user.username).first()
            user.password = request.password
            session.commit()

    @Route(route='users/{user_id}', methods=[RequestMethods.PATCH])
    @cherrypy.tools.model_params(cls=ParamsDatabaseUser)
    @cherrypy.tools.enforce_policy(policy_name="database:users:password")
    @cherrypy.tools.model_in(cls=RequestDatabaseChangePassword)
    def change_password_other(self, user_id):
        cherrypy.response.status = 204
        request: RequestDatabaseChangePassword = cherrypy.request.model
        with self.driver.database.session() as session:
            user: User = session.query(User).filter(User.id == user_id).first()

            if user is None:
                raise cherrypy.HTTPError(404, "The resource could not be found.")

            if user.username == "admin":
                raise cherrypy.HTTPError(400, "Only the admin user can change it's password.")

            user.password = request.password
            session.commit()

    @Route(route='users/{user_id}/role/add', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsDatabaseUser)
    @cherrypy.tools.enforce_policy(policy_name="database:users:role:add")
    @cherrypy.tools.model_in(cls=RequestDatabaseUserRole)
    def add_user_role(self, user_id):
        cherrypy.response.status = 204
        request: RequestDatabaseUserRole = cherrypy.request.model
        with self.driver.database.session() as session:
            user: User = session.query(User).filter(User.id == user_id).first()

            if user is None:
                raise cherrypy.HTTPError(404, "The resource could not be found.")

            if user.username == "admin":
                raise cherrypy.HTTPError(400, "Cannot change roles for the admin user.")

            user_role = UserRole()
            user_role.role = request.role
            session.add(user_role)

            user.roles.append(user_role)
            session.commit()

    @Route(route='users/{user_id}/role/remove', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsDatabaseUser)
    @cherrypy.tools.enforce_policy(policy_name="database:users:role:remove")
    @cherrypy.tools.model_in(cls=RequestDatabaseUserRole)
    def remove_user_role(self, user_id):
        cherrypy.response.status = 204
        request: RequestDatabaseUserRole = cherrypy.request.model
        with self.driver.database.session() as session:
            user: User = session.query(User).filter(User.id == user_id).first()

            if user is None:
                raise cherrypy.HTTPError(404, "The resource could not be found.")

            if user.username == "admin":
                raise cherrypy.HTTPError(400, "Cannot change roles for the admin user.")

            user_role = session.query(UserRole).join(User).filter(User.id == user_id).filter(
                UserRole.role == request.role).first()

            if user_role is None:
                raise cherrypy.HTTPError(400, "User does not have the requested role.")

            session.delete(user_role)
            session.commit()
