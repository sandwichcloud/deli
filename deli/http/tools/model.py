import logging
from urllib.parse import urlencode

import cherrypy
from cherrypy._cpcompat import ntou, json_decode, json_encode
from cherrypy.lib.jsontools import json_in
from schematics import Model
from schematics.exceptions import DataError

from deli.http.errors.validation import PayloadValidationError, ResponseValidationError


def model_in(cls):
    def model_processor(entity):
        """Read application/json data into request.model."""
        if not entity.headers.get(ntou('Content-Length'), ntou('')):  # pragma: no cover
            raise cherrypy.HTTPError(411)
        body = entity.fp.read()
        with cherrypy.HTTPError.handle(ValueError, 400, 'Invalid JSON document'):
            json = json_decode(body.decode('utf-8'))
        try:
            model = cls(json)
            model.validate()
        except DataError as e:
            raise PayloadValidationError(e)
        cherrypy.serving.request.model = model

    json_in(processor=model_processor)


def model_out(cls=None):
    def model_handler(*args, **kwargs):
        value = cherrypy.serving.request._model_inner_handler(*args, **kwargs)
        if issubclass(value.__class__, Model) is False:
            raise cherrypy.HTTPError(500, "Output Model class (" + value.__class__.__name__ +
                                     ") is not a subclass of  " + Model.__module__ + "." + Model.__name__)
        if cls is not None and value.__class__ != cls:
            raise cherrypy.HTTPError(500, "Output Model class (" + value.__class__.__name__ +
                                     ") does not match given class " + cls.__name__)
        try:
            value.validate()
        except DataError as e:
            try:
                raise ResponseValidationError(e)
            except ResponseValidationError:
                cherrypy.log.error('Error with model_out response', severity=logging.ERROR, traceback=True)
                raise

        return json_encode(value.to_native())

    request = cherrypy.serving.request
    if request.handler is None:  # pragma: no cover
        return
    request._model_inner_handler = request.handler
    request.handler = model_handler
    cherrypy.serving.response.headers['Content-Type'] = 'application/json'


def model_out_pagination(cls=None):
    def model_handler(*args, **kwargs):

        list_name = cherrypy.serving.request.path_info.split("/")[-1]
        data = {
            list_name: []
        }

        values, more_pages = cherrypy.serving.request._model_inner_handler(*args, **kwargs)
        for value in values:
            if issubclass(value.__class__, Model) is False:
                raise cherrypy.HTTPError(500, "Output Model class (" + value.__class__.__name__ +
                                         ") is not a subclass of  " + Model.__module__ + "." + Model.__name__)
            if cls is not None and value.__class__ != cls:
                raise cherrypy.HTTPError(500, "Output Model class (" + value.__class__.__name__ +
                                         ") does not match given class " + cls.__name__)
            try:
                value.validate()
            except DataError as e:
                raise ResponseValidationError(e)

            data[list_name].append(value.to_native())

        data[list_name + "_links"] = []
        if more_pages:
            req_params = cherrypy.serving.request.params

            for k, v in dict(req_params).items():
                if v is None:
                    del req_params[k]

            req_params['marker'] = data[list_name][-1]['id']
            data[list_name + "_links"] = [
                {
                    "href": cherrypy.url(qs=urlencode(req_params)),
                    "rel": "next"
                }
            ]

        return json_encode(data)

    request = cherrypy.serving.request
    if request.handler is None:  # pragma: no cover
        return
    request._model_inner_handler = request.handler
    request.handler = model_handler
    cherrypy.serving.response.headers['Content-Type'] = 'application/json'
