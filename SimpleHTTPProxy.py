#!/usr/bin/env python

import sys
import urllib2
from threading import Lock
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from cStringIO import StringIO
import gzip

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass


class HTTPNoRedirectHandler(urllib2.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        url = req.get_full_url()
        raise urllib2.HTTPError(url, code, msg, hdrs, fp)


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

        if self.command == 'POST':
            length = int(self.headers['Content-Length'])
            postdata = self.rfile.read(length)
            req = urllib2.Request(self.path, data=postdata, headers=self.headers)
        else:
            req = urllib2.Request(self.path, headers=self.headers)
        opener = urllib2.build_opener(HTTPNoRedirectHandler())
        try:
            res = opener.open(req)
        except urllib2.HTTPError as e:
            res = e

        # "The Via general-header field MUST be used by gateways and proxies ..." [RFC 2616]
        res.headers['Via'] = self.get_via_string(original=res.headers.get('Via'))

        is_gziped = res.headers.get('Content-Encoding') == 'gzip'
        data = res.read()
        if is_gziped:
            io = StringIO(data)
            with gzip.GzipFile(fileobj=io) as f:
                body = f.read()
        else:
            body = data

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

        self.send_response(res.code, res.msg)
        for k in res.headers:
            self.send_header(k, res.headers[k])
        self.end_headers()

        if self.command != 'HEAD':
            self.wfile.write(data)

            with Lock():
                self.save_handler(res, body)

        res.close()

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
