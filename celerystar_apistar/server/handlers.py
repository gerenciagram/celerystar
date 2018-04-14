from celerystar_apistar import App, http
from celerystar_apistar.codecs import OpenAPICodec
from celerystar_apistar.server.asgi import ASGIReceive, ASGIScope, ASGISend
from celerystar_apistar.server.wsgi import WSGIEnviron, WSGIStartResponse


def serve_schema(app: App):
    codec = OpenAPICodec()
    content = codec.encode(app.document)
    headers = {'Content-Type': 'application/vnd.oai.openapi'}
    return http.Response(content, headers=headers)


def serve_documentation(app: App):
    template_name = 'apistar/docs/index.html'
    return app.render_template(template_name, document=app.document)


def serve_static_wsgi(app: App, environ: WSGIEnviron, start_response: WSGIStartResponse):
    return app.statics(environ, start_response)


async def serve_static_asgi(app: App, scope: ASGIScope, receive: ASGIReceive, send: ASGISend):
    instance = app.statics(scope)
    await instance(receive, send)
