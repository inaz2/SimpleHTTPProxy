#!/usr/bin/env python

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test
import ssl

class SSLBumpProxyHandler(SimpleHTTPProxyHandler):
    keyfile = 'SSLBumpProxy/server.key'
    certfile = 'SSLBumpProxy/server.crt'
    timeout = None    # FIXME: SSL connection to the client needs to be closed every time

    def request_handler(self, req, reqbody):
        if req.command == 'CONNECT':
            self.send_response(200, 'Connection Established')
            self.end_headers()

            self.connection = ssl.wrap_socket(self.connection, keyfile=self.keyfile, certfile=self.certfile, server_side=True)
            self.rfile = self.connection.makefile("rb", self.rbufsize)
            self.wfile = self.connection.makefile("wb", self.wbufsize)

            self.https_origin = req.path.rstrip('/')
            return True
        else:
            if hasattr(self, 'https_origin'):
                req.path = self.https_origin + req.path


if __name__ == '__main__':
    test(HandlerClass=SSLBumpProxyHandler)
