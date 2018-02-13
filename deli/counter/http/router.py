from ingredients_http.router import Router


class SandwichRouter(Router):
    def paginate(self, db_cls, response_cls, limit, marker, **kwargs):
        resp_models = []

        for obj in db_cls.list(**kwargs):
            resp_models.append(response_cls.from_database(obj))

        return resp_models, False
