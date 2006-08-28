"""a WSGI application tool for CherryPy"""

import sys

import cherrypy


# is this sufficient for start_response?
def start_response(status, response_headers, exc_info=None):
    cherrypy.response.status = status
    headers_dict = dict(response_headers)
    cherrypy.response.headers.update(headers_dict)

def make_environ():
    """grabbed some of below from _cpwsgiserver.py
    
    for hosting WSGI apps in non-WSGI environments (yikes!)
    """
    
    request = cherrypy.request
    
    # create and populate the wsgi environ
    environ = dict()
    environ["wsgi.version"] = (1,0)
    environ["wsgi.url_scheme"] = request.scheme
    environ["wsgi.input"] = request.rfile
    environ["wsgi.errors"] = sys.stderr
    environ["wsgi.multithread"] = True
    environ["wsgi.multiprocess"] = False
    environ["wsgi.run_once"] = False
    environ["REQUEST_METHOD"] = request.method
    environ["SCRIPT_NAME"] = request.script_name
    environ["PATH_INFO"] = request.path_info
    environ["QUERY_STRING"] = request.query_string
    environ["SERVER_PROTOCOL"] = request.protocol
    environ["SERVER_NAME"] = request.local.name
    environ["SERVER_PORT"] = request.local.port
    environ["REMOTE_HOST"] = request.remote.name
    environ["REMOTE_ADDR"] = request.remote.ip
    environ["REMOTE_PORT"] = request.remote.port
    # then all the http headers
    headers = request.headers
    environ["CONTENT_TYPE"] = headers.get("Content-type", "")
    environ["CONTENT_LENGTH"] = headers.get("Content-length", "")
    for (k, v) in headers.iteritems():
        envname = "HTTP_" + k.upper().replace("-","_")
        environ[envname] = v
    return environ


def run(app, env=None):
    """Run the (WSGI) app and set response.body to its output"""
    try:
        environ = cherrypy.request.wsgi_environ
        environ['SCRIPT_NAME'] = cherrypy.request.script_name
        environ['PATH_INFO'] = cherrypy.request.path_info
    except AttributeError:
        environ = make_environ()
    
    if env:
        environ.update(env)
    
    # run the wsgi app and have it set response.body
    cherrypy.response.body = app(environ, start_response)
    
    return True

