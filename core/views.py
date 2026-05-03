from django.http import HttpResponse, JsonResponse
from rest_framework import permissions
from rest_framework.schemas import get_schema_view
from rest_framework.renderers import JSONOpenAPIRenderer

schema_view = get_schema_view(
    title='Travel Cambodia API',
    description='OpenAPI schema for the Travel Cambodia backend API.',
    version='1.0.0',
    permission_classes=[permissions.AllowAny],
    renderer_classes=[JSONOpenAPIRenderer],
)


def health_check(request):
    return JsonResponse({'status': 'ok'})


def api_schema_view(request):
    response = schema_view(request)
    response.accepted_renderer = JSONOpenAPIRenderer()
    response.accepted_media_type = 'application/json'
    response.renderer_context = {'request': request}
    response.render()
    return HttpResponse(response.rendered_content, content_type='application/json')


def swagger_ui_view(request):
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Travel Cambodia API Docs</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@4.21.0/swagger-ui.css" />
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@4.21.0/swagger-ui-bundle.js"></script>
  <script>
    window.onload = function () {
      const ui = SwaggerUIBundle({
        url: '/api/schema/',
        dom_id: '#swagger-ui',
        presets: [SwaggerUIBundle.presets.apis],
        layout: 'BaseLayout',
      });
      window.ui = ui;
    };
  </script>
</body>
</html>'''
    return HttpResponse(html)
