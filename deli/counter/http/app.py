import datetime
import json

from ingredients_http.app import HTTPApplication


class Application(HTTPApplication):

    def setup(self):
        super().setup()
        old_json_encoder = json.JSONEncoder.default

        def json_encoder(self, o):  # pragma: no cover
            if isinstance(o, datetime.datetime):
                return str(o.isoformat())

            return old_json_encoder(self, o)

        json.JSONEncoder.default = json_encoder
