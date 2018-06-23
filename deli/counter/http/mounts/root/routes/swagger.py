# flake8: noqa
import cherrypy
from ingredients_http.route import Route

from deli.counter.http.router import SandwichRouter


class SwaggerRouter(SandwichRouter):
    def __init__(self):
        super().__init__(uri_base='swagger')

    @Route('json')
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.json_out()
    def get(self):
        api_spec_dict = self.mount.api_spec.to_dict()
        api_spec_dict['components']['securitySchemes'] = {
            'Bearer': {'type': 'apiKey', 'name': 'Authorization', 'in': 'header'}}

        return api_spec_dict

    @Route('ui')
    @cherrypy.config(**{'tools.authentication.on': False})
    def ui(self):
        ui_html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Swagger UI</title>
  <link href="https://fonts.googleapis.com/css?family=Open+Sans:400,700|Source+Code+Pro:300,600|Titillium+Web:400,600,700" rel="stylesheet">
  <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3.17.1/swagger-ui.css" >
  <style>
    html
    {
      box-sizing: border-box;
      overflow: -moz-scrollbars-vertical;
      overflow-y: scroll;
    }

    *,
    *:before,
    *:after
    {
      box-sizing: inherit;
    }

    body
    {
      margin:0;
      background: #fafafa;
    }
  </style>
</head>

<body>
  <div id="swagger-ui"></div>

  <script src="https://unpkg.com/swagger-ui-dist@3.17.1/swagger-ui-bundle.js"></script>
  <script src="https://unpkg.com/swagger-ui-dist@3.17.1/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = function() {
      const ui = SwaggerUIBundle({
        url: "%s",
        dom_id: '#swagger-ui',
        docExpansion: 'none',
        showExtensions: true,
        presets: [
          SwaggerUIBundle.presets.apis
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ]
      })

      window.ui = ui
    }
  </script>
</body>

</html>
        """ % cherrypy.url('/swagger/json')
        return ui_html
