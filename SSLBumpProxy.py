#!/usr/bin/env python

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test
import ssl

class SSLBumpProxyHandler(SimpleHTTPProxyHandler):
    keyfile = 'SSLBumpProxy/server.key'
    certfile = 'SSLBumpProxy/server.crt'
    timeout = None    # FIXME: SSL connection to the client needs to be closed every time

    def do_CONNECT(self):
        self.send_response(200, 'Connection Established')
        self.end_headers()

        self.connection = ssl.wrap_socket(self.connection, keyfile=self.keyfile, certfile=self.certfile, server_side=True)
        self.rfile = self.connection.makefile("rb", self.rbufsize)
        self.wfile = self.connection.makefile("wb", self.wbufsize)

        self.origin = "https://%s" % self.path.replace(':443', '')

    def do_SPAM(self):
        if not self.path.startswith('http'):
            self.path = self.origin + self.path
        SimpleHTTPProxyHandler.do_SPAM(self)


if __name__ == '__main__':
    test(HandlerClass=SSLBumpProxyHandler)
