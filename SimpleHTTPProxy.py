#!/usr/bin/env python

import sys
import httplib
from urlparse import urlsplit
from threading import Lock
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from cStringIO import StringIO
import gzip
import socket

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    # listening on IPv4 address
    address_family = socket.AF_INET


class ThreadingHTTPServer6(ThreadingHTTPServer):
    # listening on IPv6 address
    address_family = socket.AF_INET6


class SimpleHTTPProxyHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.do_SPAM()

    def do_GET(self):
        self.do_SPAM()

    def do_POST(self):
        self.do_SPAM()

    def do_SPAM(self):
        req = self
        content_length = int(req.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
        else:
            body = None

        # RFC 2616 requirements
        self.modify_via_header(req.headers)
        req.headers['Connection'] = 'close'

        replaced_body = self.request_handler(req, body)
        if replaced_body is True:
            return
        elif replaced_body is not None:
            body = replaced_body

        u = urlsplit(req.path)
        if u.scheme == 'https':
            conn = httplib.HTTPSConnection(u.netloc)
        else:
            conn = httplib.HTTPConnection(u.netloc)
        selector = "%s?%s" % (u.path, u.query)
        if body:
            conn.request(req.command, selector, body, headers=dict(req.headers))
        else:
            conn.request(req.command, selector, headers=dict(req.headers))
        res = conn.getresponse()
        res.headers = res.msg    # add an alias so that res has the same interface as req

        is_gziped = res.headers.get('Content-Encoding') == 'gzip'
        data = res.read()
        if is_gziped:
            io = StringIO(data)
            with gzip.GzipFile(fileobj=io) as f:
                body = f.read()
        else:
            body = data

        conn.close()

        # RFC 2616 requirements
        self.modify_via_header(res.headers)
        res.headers['Connection'] = 'close'

        replaced_body = self.response_handler(req, res, body)
        if replaced_body is True:
            return
        elif replaced_body is not None:
            if is_gziped:
                io = StringIO()
                with gzip.GzipFile(fileobj=io, mode='wb') as f:
                    f.write(replaced_body)
                data = io.getvalue()
            else:
                data = replaced_body
            body = replaced_body

        self.send_response(res.status, res.reason)
        for k in res.headers:
            self.send_header(k, res.headers[k])
        self.end_headers()

        if self.command != 'HEAD':
            self.wfile.write(data)

            with Lock():
                self.save_handler(req, res, body)

    def modify_via_header(self, headers):
        if self.protocol_version.startswith('HTTP/'):
            via_string = "%s proxy" % self.protocol_version[5:]
        else:
            via_string = "%s proxy" % self.protocol_version

        original = headers.get('Via')
        if original:
            headers['Via'] = original + ', ' + via_string
        else:
            headers['Via'] = via_string

    def request_handler(self, req, body):
        # override here
        # return True if you sent the response here and the proxy should not connect to the upstream server
        # return replaced body (other than None and True) if you did
        pass

    def response_handler(self, req, res, body):
        # override here
        # return True if you sent the response here and the proxy should not connect to the upstream server
        # return replaced body (other than None and True) if you did
        pass

    def save_handler(self, req, res, body):
        # override here
        # this handler is called after the proxy responded to the client
        pass


def test(HandlerClass=SimpleHTTPProxyHandler, ServerClass=ThreadingHTTPServer, protocol="HTTP/1.0"):
    if sys.argv[1:]:
        port = int(sys.argv[1])
    else:
        port = 8080
    server_address = ('', port)

    HandlerClass.protocol_version = protocol
    httpd = ServerClass(server_address, HandlerClass)

    sa = httpd.socket.getsockname()
    print "Serving HTTP on", sa[0], "port", sa[1], "..."
    httpd.serve_forever()


if __name__ == '__main__':
    test()

    # use below for listening on IPv6 address
    # test(ServerClass=ThreadingHTTPServer6)
