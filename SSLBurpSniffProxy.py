#!/usr/bin/env python

from SSLBurpProxy import SSLBurpProxyHandler, test
import urlparse

class SSLBurpSniffProxyHandler(SSLBurpProxyHandler):
    def request_handler(self, req, body):
        SSLBurpProxyHandler.request_handler(self, req, body)

        if req.command == 'POST' and req.headers.get('Content-Type').startswith('application/x-www-form-urlencoded'):
            print req.path
            for k, v in urlparse.parse_qsl(body):
                print "  %s: %s" % (k, v)


if __name__ == '__main__':
    test(HandlerClass=SSLBurpSniffProxyHandler)
