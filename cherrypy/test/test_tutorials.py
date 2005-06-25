"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import unittest
import sys

import cherrypy
from cherrypy.test import helper

server_conf = {'server.socketHost': helper.HOST,
               'server.socketPort': helper.PORT,
               'server.threadPool': 10,
               'server.logToScreen': False,
               'server.environment': "production",
##               'profiling.on': True,
               }

def load_tut_module(tutorialName):
    """Import or reload tutorial module as needed."""
    cherrypy.config.reset()
    cherrypy.config.update({'global': server_conf.copy()})
    
    target = "cherrypy.tutorial." + tutorialName
    if target in sys.modules:
        module = reload(sys.modules[target])
    else:
        module = __import__(target)
    
    cherrypy.server.start(initOnly=True)


class TutorialTest(unittest.TestCase):
    
    def test01HelloWorld(self):
        load_tut_module("tut01_helloworld")
        helper.request("/")
        self.assertEqual(cherrypy.response.body, 'Hello world!')
    
    def test02ExposeMethods(self):
        load_tut_module("tut02_expose_methods")
        helper.request("/showMessage")
        self.assertEqual(cherrypy.response.body, 'Hello world!')
    
    def test03GetAndPost(self):
        load_tut_module("tut03_get_and_post")
        
        # Try different GET queries
        helper.request("/greetUser?name=Bob")
        self.assertEqual(cherrypy.response.body, "Hey Bob, what's up?")
        
        helper.request("/greetUser")
        self.assertEqual(cherrypy.response.body,
                         'Please enter your name <a href="./">here</a>.')
        
        helper.request("/greetUser?name=")
        self.assertEqual(cherrypy.response.body,
                         'No, really, enter your name <a href="./">here</a>.')
        
        # Try the same with POST
        helper.request("/greetUser", method="POST", body="name=Bob")
        self.assertEqual(cherrypy.response.body, "Hey Bob, what's up?")
        
        helper.request("/greetUser", method="POST", body="name=")
        self.assertEqual(cherrypy.response.body,
                         'No, really, enter your name <a href="./">here</a>.')
    
    def test04ComplexSite(self):
        load_tut_module("tut04_complex_site")
        msg = '''
            <p>Here are some extra useful links:</p>
            
            <ul>
                <li><a href="http://del.icio.us">del.icio.us</a></li>
                <li><a href="http://www.mornography.de">Hendrik's weblog</a></li>
            </ul>
            
            <p>[<a href="../">Return to links page</a>]</p>'''
        helper.request("/links/extra/")
        self.assertEqual(cherrypy.response.body, msg)
    
    def test05DerivedObjects(self):
        load_tut_module("tut05_derived_objects")
        msg = '''
            <html>
            <head>
                <title>Another Page</title>
            <head>
            <body>
            <h2>Another Page</h2>
        
            <p>
            And this is the amazing second page!
            </p>
        
            </body>
            </html>
        '''
        helper.request("/another/")
        self.assertEqual(cherrypy.response.body, msg)
    
    def test06DefaultMethod(self):
        load_tut_module("tut06_default_method")
        helper.request('/hendrik')
        self.assertEqual(cherrypy.response.body,
                         'Hendrik Mans, CherryPy co-developer & crazy German '
                         '(<a href="./">back</a>)')
    def test07Sessions(self):
        load_tut_module("tut07_sessions")
        cherrypy.config.update({"global": {"sessionFilter.on": True}})
        
        helper.request('/')
        self.assertEqual(cherrypy.response.body,
                         "\n            During your current session, you've viewed this"
                         "\n            page 1 times! Your life is a patio of fun!"
                         "\n        ")
        
        helper.request('/', [('Cookie', dict(cherrypy.response.headers)['Set-Cookie'])])
        self.assertEqual(cherrypy.response.body,
                         "\n            During your current session, you've viewed this"
                         "\n            page 2 times! Your life is a patio of fun!"
                         "\n        ")
    
    def test08GeneratorsAndYield(self):
        load_tut_module("tut08_generators_and_yield")
        helper.request('/')
        self.assertEqual(cherrypy.response.body,
                         '<html><body><h2>Generators rule!</h2>'
                         '<h3>List of users:</h3>'
                         'Remi<br/>Carlos<br/>Hendrik<br/>Lorenzo Lamas<br/>'
                         '</body></html>')
    def test09SessionFilter(self):
        load_tut_module("tut09_sessionfilter")
        cherrypy.config.update({"global": {"sessionFilter.on": True}})
        
        helper.request('/')
        self.assert_("viewed this page 1 times" in cherrypy.response.body)
        
        helper.request('/', [('Cookie', dict(cherrypy.response.headers)['Set-Cookie'])])
        self.assert_("viewed this page 2 times" in cherrypy.response.body)
    
    def test10FileUpload(self):
        load_tut_module("tut10_file_upload")
        
        h = [("Content-type", "multipart/form-data; boundary=x"),
             ("Content-Length", "110")]
        b = """--x
Content-Disposition: form-data; name="myFile"; filename="hello.txt"
Content-Type: text/plain

hello
--x--
"""
        helper.request('/upload', h, "POST", b)
        self.assertEqual(cherrypy.response.body, '''
        <html><body>
            myFile length: 5<br />
            myFile filename: hello.txt<br />
            myFile mime-type: text/plain
        </body></html>
        ''')

if __name__ == "__main__":
    unittest.main()

