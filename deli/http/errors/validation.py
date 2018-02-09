import json

import cherrypy
from cherrypy._cperror import HTTPError, _be_ie_unfriendly, clean_headers
from schematics.datastructures import FrozenDict
from schematics.exceptions import DataError


def json_errors_to_json(validation_errors, root=None):
    json_errors = []
    for key, value in validation_errors.items():
        if isinstance(value, dict):
            json_errors.extend(json_errors_to_json(value, root=key))
        else:
            if isinstance(value, str):
                json_errors.append({
                    'detail': value,
                    'source': {
                        'pointer': root + "/" + key
                    }
                })
            elif isinstance(value, FrozenDict):
                for k in value.keys():
                    for field in value[k].keys():
                        json_errors.extend(json_errors_to_json({str(k): value[k][field]}, root=root + "/" + key))
            else:
                for error in value:
                    json_errors.append({
                        'detail': error.summary,
                        'source': {
                            'pointer': root + "/" + key
                        }
                    })
    return json_errors


def param_errors_to_json(validation_errors):
    json_errors = []
    for key, value in validation_errors.items():
        if isinstance(value, dict):
            json_errors.extend(param_errors_to_json(value))
        else:
            if isinstance(value, str):
                json_errors.append({
                    'detail': value,
                    'source': {
                        'parameter': key
                    }
                })
            else:
                for error in value:
                    json_errors.append({
                        'detail': error.summary,
                        'source': {
                            'parameter': key
                        }
                    })
    return json_errors


class ParamValidationError(HTTPError):
    def __init__(self, error):
        super(ParamValidationError, self).__init__(400)
        if not isinstance(error, DataError):  # pragma: no cover
            raise ValueError("error must be instance of DataError")
        self.error = error

    def set_response(self):
        response = cherrypy.serving.response
        clean_headers(self.code)
        response.status = self.status
        response.headers.pop('Content-Length', None)
        data = {
            "status": "%s %s" % (self.status, self.reason),
            "message": "Query parameters are invalid or misconfigured.",
            'errors': param_errors_to_json(self.error.errors)
        }
        content = json.dumps(data)
        response.headers['Content-Type'] = 'application/json'
        response.body = bytes(content, encoding='utf-8')
        _be_ie_unfriendly(self.code)


class PayloadValidationError(HTTPError):
    def __init__(self, error):
        super(PayloadValidationError, self).__init__(422)
        if not isinstance(error, DataError):  # pragma: no cover
            raise ValueError("error must be instance of DataError")
        self.error = error

    def set_response(self):
        response = cherrypy.serving.response
        clean_headers(self.code)
        response.status = self.status
        response.headers.pop('Content-Length', None)
        data = {
            "status": "%s %s" % (self.status, self.reason),
            "message": "Data payload invalid or misconfigured.",
            'errors': json_errors_to_json(self.error.errors, '/data/attributes')
        }
        content = json.dumps(data)
        response.headers['Content-Type'] = 'application/json'
        response.body = bytes(content, encoding='utf-8')
        _be_ie_unfriendly(self.code)


class ResponseValidationError(HTTPError):
    def __init__(self, error):
        super(ResponseValidationError, self).__init__(500)
        if not isinstance(error, DataError):  # pragma: no cover
            raise ValueError("error must be instance of DataError")
        self.error = error

    def set_response(self):
        response = cherrypy.serving.response
        clean_headers(self.code)
        response.status = self.status
        response.headers.pop('Content-Length', None)
        data = {
            "status": "%s %s" % (self.status, self.reason),
            "message": "Server response invalid or misconfigured.",
            'errors': json_errors_to_json(self.error.errors, '/data/attributes')
        }
        content = json.dumps(data)
        response.headers['Content-Type'] = 'application/json'
        response.body = bytes(content, encoding='utf-8')
        _be_ie_unfriendly(self.code)
