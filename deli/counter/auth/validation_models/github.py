from schematics import Model
from schematics.types import StringType


class RequestGithubToken(Model):
    authorizationCode = StringType(required=True)


class RequestGithubAuthorization(Model):
    username = StringType(required=True)
    password = StringType(required=True)
    otp_code = StringType()
