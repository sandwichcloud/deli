import cherrypy
from schematics.exceptions import DataError

from deli.http.errors.validation import ParamValidationError


def model_params(cls):
    try:
        model = cls(cherrypy.request.params)
        model.validate()
    except DataError as e:
        raise ParamValidationError(e)

    cherrypy.request.params = model.to_native()
