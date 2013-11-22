#!/usr/bin/env python

import sys
import httplib
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from threading import Lock, RLock, Thread, Event
from cStringIO import StringIO
from urlparse import urlsplit
import socket
import select
import gzip
import zlib
import re
import traceback


class RestartableTimer(Thread):
    def __init__(self, interval, function, args=[], kwargs={}):
        Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.finished = Event()
        self.restarted = True

    def cancel(self):
        self.finished.set()

    def run(self):
        while self.restarted:
            self.restarted = False
            self.finished.wait(self.interval)
        if not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
        self.finished.set()

    def restart(self):
        self.restarted = True
        self.finished.set()


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    # listening on IPv4 address
    address_family = socket.AF_INET

    def handle_error(self, request, client_address):
        # override SocketServer.BaseServer
        print >>sys.stderr, '-'*40
        print >>sys.stderr, 'Exception happened during processing of request from', client_address
        traceback.print_exc()
        print >>sys.stderr, '-'*40


class ThreadingHTTPServer6(ThreadingHTTPServer):
    # listening on IPv6 address
    address_family = socket.AF_INET6


class SimpleHTTPProxyHandler(BaseHTTPRequestHandler):
    global_lock = Lock()
    conn_table = {}
    timeout = 2               # timeout with clients, set to None not to make persistent connection
    upstream_timeout = 115    # timeout with upstream servers, set to None not to make persistent connection
    proxy_via = None          # pseudonym of the proxy in Via header, set to None not to modify original Via header

    def do_CONNECT(self):
        # just provide a tunnel, transfer the data with no modification
        # override here if you need

        req = self
        reqbody = None
        req.path = "https://%s/" % req.path.replace(':443', '')

        replaced_reqbody = self.request_handler(req, reqbody)
        if replaced_reqbody is True:
            return

        u = urlsplit(req.path)
        address = (u.hostname, u.port or 443)
        try:
            conn = socket.create_connection(address)
        except socket.error:
            self.send_error(504)    # 504 Gateway Timeout
            return
        self.send_response(200, 'Connection Established')
        self.end_headers()

        conns = [self.connection, conn]
        keep_connection = True
        while keep_connection:
            keep_connection = False
            rlist, wlist, xlist = select.select(conns, [], conns, self.timeout)
            if xlist:
                break
            for r in rlist:
                other = conns[1] if r is conns[0] else conns[0]
                data = r.recv(8192)
                if data:
                    other.sendall(data)
                    keep_connection = True
        conn.close()

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
            reqbody = self.rfile.read(content_length)
        else:
            reqbody = None

        replaced_reqbody = self.request_handler(req, reqbody)
        if replaced_reqbody is True:
            return
        elif replaced_reqbody is not None:
            reqbody = replaced_reqbody
            if 'Content-Length' in req.headers:
                req.headers['Content-Length'] = str(len(reqbody))

        # follow RFC 2616 requirements
        self.remove_hop_by_hop_headers(req.headers)
        if self.upstream_timeout:
            req.headers['Connection'] = 'Keep-Alive'
        else:
            req.headers['Connection'] = 'close'
        if self.proxy_via:
            self.modify_via_header(req.headers)

        try:
            res, resdata = self.request_to_upstream_server(req, reqbody)
        except socket.error:
            self.send_error(504)    # 504 Gateway Timeout
            return

        content_encoding = res.headers.get('Content-Encoding', 'identity')
        resbody = self.decode_content_body(resdata, content_encoding)

        replaced_resbody = self.response_handler(req, reqbody, res, resbody)
        if replaced_resbody is True:
            return
        elif replaced_resbody is not None:
            resdata = self.encode_content_body(replaced_resbody, content_encoding)
            if 'Content-Length' in res.headers:
                res.headers['Content-Length'] = str(len(resdata))
            resbody = replaced_resbody

        # follow RFC 2616 requirements
        self.remove_hop_by_hop_headers(res.headers)
        if self.timeout:
            res.headers['Connection'] = 'Keep-Alive'
        else:
            res.headers['Connection'] = 'close'
        if self.proxy_via:
            self.modify_via_header(res.headers)

        self.send_response(res.status, res.reason)
        for k, v in res.headers.items():
            if k == 'set-cookie':
                # Origin servers SHOULD NOT fold multiple Set-Cookie header fields into a single header field. [RFC 6265]
                for value in self.split_set_cookie_header(v):
                    self.send_header(k, value)
            else:
                self.send_header(k, v)
        self.end_headers()

        if self.command != 'HEAD':
            self.wfile.write(resdata)
            with self.global_lock:
                self.save_handler(req, reqbody, res, resbody)

    def request_to_upstream_server(self, req, reqbody):
        u = urlsplit(req.path)
        origin = (u.scheme, u.netloc)

        # An HTTP/1.1 proxy MUST ensure that any request message it forwards does contain 
        # an appropriate Host header field that identifies the service being requested by the proxy. [RFC 2616]
        req.headers['Host'] = u.netloc
        selector = "%s?%s" % (u.path, u.query) if u.query else u.path

        while True:
            with self.lock_origin(origin):
                conn, timer = self.open_origin(origin)
                try:
                    conn.request(req.command, selector, reqbody, headers=dict(req.headers))
                except socket.error:
                    # Couldn't connect to the upstream server.
                    self.close_origin(origin)
                    raise
                try:
                    res = conn.getresponse(buffering=True)
                except httplib.BadStatusLine as e:
                    if e.line == "''":
                        # Presumably, the connection had been closed by the server.
                        # Go for a retry with a new connection.
                        self.close_origin(origin)
                        continue
                    else:
                        raise
                resdata = res.read()
                res.headers = res.msg    # so that res have the same attribute as req
                if not timer or 'close' in res.headers.get('Connection', ''):
                    self.close_origin(origin)
                else:
                    timer.restart()
            return res, resdata

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
                timer = RestartableTimer(self.upstream_timeout, self.close_origin, args=[origin])
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
        via_string = "%s %s" % (self.protocol_version, self.proxy_via)
        via_string = re.sub(r'^HTTP/', '', via_string)

        original = headers.get('Via')
        if original:
            headers['Via'] = original + ', ' + via_string
        else:
            headers['Via'] = via_string

    def decode_content_body(self, data, content_encoding):
        if content_encoding in ('gzip', 'x-gzip'):
            io = StringIO(data)
            with gzip.GzipFile(fileobj=io) as f:
                body = f.read()
        elif content_encoding == 'deflate':
            body = zlib.decompress(data)
        elif content_encoding == 'identity':
            body = data
        else:
            raise Exception("Unknown Content-Encoding: %s" % content_encoding)
        return body

    def encode_content_body(self, body, content_encoding):
        if content_encoding in ('gzip', 'x-gzip'):
            io = StringIO()
            with gzip.GzipFile(fileobj=io, mode='wb') as f:
                f.write(body)
            data = io.getvalue()
        elif content_encoding == 'deflate':
            data = zlib.compress(body)
        elif content_encoding == 'identity':
            data = body
        else:
            raise Exception("Unknown Content-Encoding: %s" % content_encoding)
        return data

    def split_set_cookie_header(self, value):
        re_cookies = r'([^=]+=[^,;]+(?:;\s*Expires=[^,]+,[^,;]+|;[^,;]+)*)(?:,\s*)?'
        return re.findall(re_cookies, value, flags=re.IGNORECASE)

    def request_handler(self, req, reqbody):
        # override here
        # return True if you sent the response here and the proxy should not connect to the upstream server
        # return replaced reqbody (other than None and True) if you did
        pass

    def response_handler(self, req, reqbody, res, resbody):
        # override here
        # return True if you sent the response here and the proxy should not connect to the upstream server
        # return replaced resbody (other than None and True) if you did
        pass

    def save_handler(self, req, reqbody, res, resbody):
        # override here
        # this handler is called after the proxy sent a response to the client
        # this handler is thread-safe, because this handler is always called with a global lock
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
