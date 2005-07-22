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

import os, os.path
import sys
import time
import socket
import StringIO
import threading

import cherrypy
import webtest
import types
for _x in dir(cherrypy):
    y = getattr(cherrypy, _x)
    if isinstance(y, types.ClassType) and issubclass(y, cherrypy.Error):
        webtest.ignored_exceptions.append(y)


def startServer(serverClass=None):
    """Start the given server (default serverless) in a new thread."""
    if serverClass is None:
        cherrypy.server.start(initOnly=True)
    else:
        t = threading.Thread(target=cherrypy.server.start,
                             args=(False, serverClass))
        t.start()
        time.sleep(1)


def stopServer():
    """Stop the current CP server."""
    cherrypy.server.stop()
    if cherrypy.config.get('server.threadPool') > 1:
        # With thread-pools, it can take up to 1 sec for the server to stop
        time.sleep(1.1)


def onerror():
    """Assign to _cpOnError to enable webtest server-side debugging."""
    handled = webtest.server_error()
    if not handled:
        cherrypy._cputil._cpOnError()


class CPWebCase(webtest.WebCase):
    
    def _getRequest(self, url, headers, method, body):
        # Like getPage, but for serverless requests.
        webtest.ServerError.on = False
        self.url = url
        
        requestLine = "%s %s HTTP/1.1" % (method.upper(), url)
        headers = webtest.cleanHeaders(headers, method, body,
                                       self.HOST, self.PORT)
        if body is not None:
            body = StringIO.StringIO(body)
        
        cherrypy.server.request(self.HOST, self.HOST, requestLine,
                                headers, body, "http")
        
        self.status = cherrypy.response.status
        self.headers = cherrypy.response.headers
        try:
            self.body = []
            for chunk in cherrypy.response.body:
                self.body.append(chunk)
        except:
            if cherrypy.config.get("server.protocolVersion") == "HTTP/1.0":
                # Pass the error through
                raise
            
            from cherrypy import _cphttptools
            s, h, b = _cphttptools.bareError()
            # Don't reset status or headers; we're emulating an error which
            # occurs after status and headers have been written to the client.
            for chunk in b:
                self.body.append(chunk)
        self.body = "".join(self.body)
        
        if webtest.ServerError.on:
            raise webtest.ServerError
    
    def getPage(self, url, headers=None, method="GET", body=None):
        """Open the url with debugging support. Return status, headers, body."""
        # Install a custom error handler, so errors in the server will:
        # 1) show server tracebacks in the test output, and
        # 2) stop the HTTP request (if any) and ignore further assertions.
        cherrypy.root._cpOnError = onerror
        
        if cherrypy._httpserver is None:
            self._getRequest(url, headers, method, body)
        else:
            webtest.WebCase.getPage(self, url, headers, method, body)

CPTestLoader = webtest.ReloadingTestLoader()
CPTestRunner = webtest.TerseTestRunner(verbosity=2)


def run_test_suite(moduleNames, server, conf):
    """Run the given test modules using the given server and conf.
    
    The server is started and stopped once, regardless of the number
    of test modules. The config, however, is reset for each module.
    """
    if isinstance(conf, basestring):
        # assume it's a filename
        cherrypy.config.update(file=conf)
    else:
        cherrypy.config.update(conf.copy())
    startServer(server)
    for testmod in moduleNames:
        # Must run each module in a separate suite,
        # because each module uses/overwrites cherrypy globals.
        cherrypy.config.reset()
        if isinstance(conf, basestring):
            cherrypy.config.update(file=conf)
        else:
            cherrypy.config.update(conf.copy())
        cherrypy._cputil._cpInitDefaultFilters()
        
        suite = CPTestLoader.loadTestsFromName(testmod)
        CPTestRunner.run(suite)
    stopServer()


def testmain(server=None, conf=None):
    """Run __main__ as a test module, with webtest debugging."""
    if conf is None:
        conf = {}
    if isinstance(conf, basestring):
        # assume it's a filename
        cherrypy.config.update(file=conf)
    else:
        cherrypy.config.update(conf.copy())
    
    startServer(server)
    try:
        cherrypy._cputil._cpInitDefaultFilters()
        webtest.main()
    finally:
        # webtest.main == unittest.main, which raises SystemExit,
        # so put stopServer in a finally clause
        stopServer()

