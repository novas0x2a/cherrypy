from cherrypy.test import test
test.prefer_parent_path()


def setup_server():
    import os
    curdir = os.path.join(os.getcwd(), os.path.dirname(__file__))
    
    import cherrypy
    
    def test_app(environ, start_response):
        status = '200 OK'
        response_headers = [('Content-type', 'text/plain')]
        start_response(status, response_headers)
        output = ['Hello, world!\n',
                  'This is a wsgi app running within CherryPy!\n\n']
        keys = environ.keys()
        keys.sort()
        for k in keys:
            output.append('%s: %s\n' % (k,environ[k]))
        return output

    def test_empty_string_app(environ, start_response):
        status = '200 OK'
        response_headers = [('Content-type', 'text/plain')]
        start_response(status, response_headers)
        return ['Hello', '', ' ', '', 'world']
    
    def reversing_middleware(app):
        def _app(environ, start_response):
            results = app(environ, start_response)
            if not isinstance(results, basestring):
                results = "".join(results)
            results = list(results)
            results.reverse()
            return ["".join(results)]
        return _app
    
    class Root:
        def index(self):
            return "I'm a regular CherryPy page handler!"
        index.exposed = True
    
    
    cherrypy.config.update({'environment': 'test_suite'})
    cherrypy.tree.mount(Root())
    
    cherrypy.tree.graft(test_app, '/hosted/app1')
    cherrypy.tree.graft(test_empty_string_app, '/hosted/app3')
    
    # Set script_name explicitly to None to signal CP that it should
    # be pulled from the WSGI environ each time.
    app = cherrypy.Application(Root(), script_name=None)
    cherrypy.tree.graft(reversing_middleware(app), '/hosted/app2')

from cherrypy.test import helper


class WSGIGraftTests(helper.CPWebCase):
    
    wsgi_output = '''Hello, world!
This is a wsgi app running within CherryPy!'''

    def test_01_standard_app(self):
        self.getPage("/")
        self.assertBody("I'm a regular CherryPy page handler!")
    
    def test_04_pure_wsgi(self):
        self.getPage("/hosted/app1")
        self.assertHeader("Content-Type", "text/plain")
        self.assertInBody(self.wsgi_output)

    def test_05_wrapped_cp_app(self):
        self.getPage("/hosted/app2/")
        body = list("I'm a regular CherryPy page handler!")
        body.reverse()
        body = "".join(body)
        self.assertInBody(body)

    def test_06_empty_string_app(self):
        self.getPage("/hosted/app3")
        self.assertHeader("Content-Type", "text/plain")
        self.assertInBody('Hello world')

if __name__ == '__main__':
    setup_server()
    helper.testmain()

