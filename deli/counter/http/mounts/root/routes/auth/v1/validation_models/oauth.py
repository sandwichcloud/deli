from ingredients_http.schematics.types import ArrowType
from schematics import Model
from schematics.types import EmailType, StringType


class RequestOAuthToken(Model):
    email = EmailType(required=True)
    password = StringType(min_length=1, required=True)
    otp_code = StringType()


class ResponseOAuthToken(Model):
    access_token = StringType(required=True)
    expiry = ArrowType(required=True)
