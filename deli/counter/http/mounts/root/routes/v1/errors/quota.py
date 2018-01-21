from cherrypy import HTTPError


class QuotaError(HTTPError):

    def __init__(self, resource_name, requested, used, allowed):
        super().__init__(status=400,
                         message="Quota exceeded for %(name)s: Requested %(requested)d, but already used %(used)d "
                                 "of %(allowed)d" % {"name": resource_name, "requested": requested, "used": used,
                                                     "allowed": allowed})
