#!/usr/bin/env python

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test
import ssl
import os
import urlparse
from subprocess import Popen, PIPE

class SSLBumpProxyHandler(SimpleHTTPProxyHandler):
    timeout = None    # FIXME: SSL connection to the client needs to be closed every time
    keyfile = 'SSLBumpProxy/server.key'
    certfile = 'SSLBumpProxy/server.crt'
    ca_keyfile = 'SSLBumpProxy/ca.key'
    ca_certfile = 'SSLBumpProxy/ca.crt'
    dynamic_certdir = 'SSLBumpProxy/dynamic/'    # set None if you use a static certificate

    def request_handler(self, req, reqbody):
        if req.command == 'CONNECT':
            self.send_response(200, 'Connection Established')
            self.send_header('Connection', 'Keep-Alive')
            self.end_headers()

            if self.dynamic_certdir:
                if not os.path.isdir(self.dynamic_certdir):
                    os.makedirs(self.dynamic_certdir)

                u = urlparse.urlsplit(req.path)
                certpath = "%s/%s.crt" % (self.dynamic_certdir.rstrip('/'), u.hostname)
                with self.global_lock:
                    if not os.path.isfile(certpath):
                        p1 = Popen(["openssl", "req", "-new", "-key", self.keyfile, "-subj", "/CN=%s" % u.hostname], stdout=PIPE)
                        p2 = Popen(["openssl", "x509", "-req", "-days", "3650", "-CA", self.ca_certfile, "-CAkey", self.ca_keyfile, "-CAcreateserial", "-out", certpath], stdin=p1.stdout, stderr=PIPE)
                        p1.stdout.close()
                        p2.communicate()
                self.connection = ssl.wrap_socket(self.connection, keyfile=self.keyfile, certfile=certpath, server_side=True)
            else:
                self.connection = ssl.wrap_socket(self.connection, keyfile=self.keyfile, certfile=self.certfile, server_side=True)
            self.rfile = self.connection.makefile("rb", self.rbufsize)
            self.wfile = self.connection.makefile("wb", self.wbufsize)

            self.https_origin = req.path.rstrip('/')
            return True
        elif req.command == 'GET' and req.path == 'http://cacert.test/':
            with open(self.ca_certfile, 'rb') as f:
                data = f.read()

            self.send_response(200)
            self.send_header('Content-Type', 'application/x-x509-ca-cert')
            self.send_header('Content-Length', len(data))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(data)
            return True
        else:
            if hasattr(self, 'https_origin'):
                req.path = self.https_origin + req.path


if __name__ == '__main__':
    test(HandlerClass=SSLBumpProxyHandler)
