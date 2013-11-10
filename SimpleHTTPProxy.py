#!/usr/bin/env python

import sys
import httplib
from urlparse import urlsplit
from threading import Lock, RLock, Thread, Event
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from cStringIO import StringIO
import gzip
import zlib
import socket
import re

class ResettableTimer(Thread):
    def __init__(self, interval, function, args=[], kwargs={}):
        Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.finished = Event()
        self.resetted = True

    def cancel(self):
        self.finished.set()

    def run(self):
        while self.resetted:
            self.resetted = False
            self.finished.wait(self.interval)
        if not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
        self.finished.set()

    def reset(self):
        self.resetted = True
        self.finished.set()


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    # listening on IPv4 address
    address_family = socket.AF_INET


class ThreadingHTTPServer6(ThreadingHTTPServer):
    # listening on IPv6 address
    address_family = socket.AF_INET6


class SimpleHTTPProxyHandler(BaseHTTPRequestHandler):
    global_lock = Lock()
    conn_table = {}
    timeout = 2               # timeout with clients, set to None not to make persistent connection
    upstream_timeout = 115    # timeout with upstream servers, set to None not to make persistent connection

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

        replaced_body = self.request_handler(req, body)
        if replaced_body is True:
            return
        elif replaced_body is not None:
            body = replaced_body
            if 'Content-Length' in req.headers:
                req.headers['Content-Length'] = str(len(body))
        u = urlsplit(req.path)
        origin = (u.scheme, u.netloc)

        # RFC 2616 requirements
        self.remove_hop_by_hop_headers(req.headers)
        self.modify_via_header(req.headers)
        req.headers['Host'] = u.netloc
        if self.upstream_timeout:
            req.headers['Connection'] = 'Keep-Alive'
        else:
            req.headers['Connection'] = 'close'

        while True:
            with self.lock_origin(origin):
                conn, timer = self.open_origin(origin)
                selector = "%s?%s" % (u.path, u.query)
                try:
                    conn.request(req.command, selector, body, headers=dict(req.headers))
                    # for SSLSocket.recv(), passing a non-zero flags argument is not allowed
                    if not isinstance(conn, httplib.HTTPSConnection) and not conn.sock.recv(32, socket.MSG_PEEK):
                        self.close_origin(origin)
                        continue
                    res = conn.getresponse(buffering=True)
                    data = res.read()
                except socket.error:
                    self.send_gateway_timeout()
                    self.close_origin(origin)
                    return
                res.headers = res.msg    # so that res have the same attribute as req
                if not timer or 'close' in res.headers.get('Connection', ''):
                    self.close_origin(origin)
                else:
                    timer.reset()
            break

        content_encoding = res.headers.get('Content-Encoding', 'identity')
        if content_encoding in ('gzip', 'x-gzip'):
            io = StringIO(data)
            with gzip.GzipFile(fileobj=io) as f:
                body = f.read()
        elif content_encoding == 'deflate':
            body = zlib.decompress(data)
        else:
            body = data

        replaced_body = self.response_handler(req, res, body)
        if replaced_body is True:
            return
        elif replaced_body is not None:
            if content_encoding in ('gzip', 'x-gzip'):
                io = StringIO()
                with gzip.GzipFile(fileobj=io, mode='wb') as f:
                    f.write(replaced_body)
                data = io.getvalue()
            elif content_encoding == 'deflate':
                data = zlib.compress(replaced_body)
            else:
                data = replaced_body
            if 'Content-Length' in res.headers:
                res.headers['Content-Length'] = str(len(data))
            body = replaced_body

        # RFC 2616 requirements
        self.remove_hop_by_hop_headers(res.headers)
        self.modify_via_header(res.headers)
        if self.timeout:
            res.headers['Connection'] = 'Keep-Alive'
        else:
            res.headers['Connection'] = 'close'

        self.send_response(res.status, res.reason)
        for k in res.headers:
            # Origin servers SHOULD NOT fold multiple Set-Cookie header fields into a single header field. [RFC 6265]
            if k == 'set-cookie':
                re_cookies = r'([^=]+=[^,;]+(?:;\s*Expires=[^,]+,[^,;]+|;[^,;]+)*)(?:,\s*)?'
                for m in re.finditer(re_cookies, res.headers[k], flags=re.IGNORECASE):
                    self.send_header(k, m.group(1))
                continue
            self.send_header(k, res.headers[k])
        self.end_headers()

        if self.command != 'HEAD':
            self.wfile.write(data)

            with self.global_lock:
                self.save_handler(req, res, body)

    def lock_origin(self, origin):
        d = self.conn_table.setdefault(origin, {})
        if not 'rlock' in d:
            d['rlock'] = RLock()
        return d['rlock']

    def open_origin(self, origin):
        if 'connection' in self.conn_table[origin]:
            conn, timer = self.conn_table[origin]['connection']
        else:
            scheme, netloc = origin
            if scheme == 'https':
                conn = httplib.HTTPSConnection(netloc)
            else:
                conn = httplib.HTTPConnection(netloc)
            if self.upstream_timeout:
                timer = ResettableTimer(self.upstream_timeout, self.close_origin, args=[origin])
                timer.daemon = True
                timer.start()
            else:
                timer = None
            self.conn_table[origin]['connection'] = (conn, timer)
        return conn, timer

    def close_origin(self, origin):
        with self.lock_origin(origin):
            conn, timer = self.conn_table[origin]['connection']
            if timer:
                timer.cancel()
            conn.close()
            del self.conn_table[origin]['connection']

    def send_gateway_timeout(self):
        headers = {}
        self.modify_via_header(headers)
        headers['Connection'] = 'close'

        self.send_response(504)
        for k in headers:
            self.send_header(k, headers[k])
        self.end_headers()
        self.wfile.write('504 Gateway Timeout')

    def remove_hop_by_hop_headers(self, headers):
        hop_by_hop_headers = ['Connection', 'Keep-Alive', 'Proxy-Authenticate', 'Proxy-Authorization', 'TE', 'Trailers', 'Trailer', 'Transfer-Encoding', 'Upgrade']
        connection = headers.get('Connection')
        if connection:
            keys = re.split(r',\s*', connection)
            hop_by_hop_headers.extend(keys)

        for k in hop_by_hop_headers:
            if k in headers:
                del headers[k]

    def modify_via_header(self, headers):
        via_string = "%s proxy" % re.sub(r'^HTTP/', '', self.protocol_version)

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


def test(HandlerClass=SimpleHTTPProxyHandler, ServerClass=ThreadingHTTPServer, protocol="HTTP/1.1"):
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
