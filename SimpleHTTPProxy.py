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
        is_resolved = self.request_handler()
        if is_resolved:
            return

        # "The Via general-header field MUST be used by gateways and proxies ..." [RFC 2616]
        self.headers['Via'] = self.get_via_string(original=self.headers.get('Via'))

        requrl = urlsplit(self.path)
        conn = httplib.HTTPConnection(requrl.netloc)
        reqpath = "%s?%s" % (requrl.path, requrl.query)
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            conn.request(self.command, reqpath, body, headers=dict(self.headers))
        else:
            conn.request(self.command, reqpath, headers=dict(self.headers))
        res = conn.getresponse()
        setattr(res, 'headers', res.msg)    # just hack

        is_gziped = res.headers.get('Content-Encoding') == 'gzip'
        data = res.read()
        if is_gziped:
            io = StringIO(data)
            with gzip.GzipFile(fileobj=io) as f:
                body = f.read()
        else:
            body = data

        conn.close()

        # "The Via general-header field MUST be used by gateways and proxies ..." [RFC 2616]
        res.headers['Via'] = self.get_via_string(original=res.headers.get('Via'))

        replaced_body = self.response_handler(res, body)
        if replaced_body:
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
                self.save_handler(res, body)

    def get_via_string(self, original=None):
        if self.protocol_version.startswith('HTTP/'):
            via_string = "%s proxy" % self.protocol_version[5:]
        else:
            via_string = "%s proxy" % self.protocol_version

        if original:
            return original + ', ' + via_string
        else:
            return via_string

    def request_handler(self):
        # override here
        # return True if the response resolved, i.e., if the proxy should not connect to the upstream server
        pass

    def response_handler(self, res, body):
        # override here
        # return replaced body if you did
        pass

    def save_handler(self, res, body):
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
