from schematics import Model
from schematics.types import StringType, ListType

from deli.http.schematics.types import ArrowType, KubeName


class RequestScopeToken(Model):
    project_id = KubeName(required=True)


class ResponseVerifyToken(Model):
    username = StringType()
    driver = StringType()
    service_account_name = StringType()
    project = KubeName()
    global_roles = ListType(StringType(), default=list)
    project_roles = ListType(StringType(), default=list)


class ResponseOAuthToken(Model):
    access_token = StringType(required=True)
    expiry = ArrowType(required=True)
