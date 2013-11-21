#!/usr/bin/env python

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test
import re

class DenyProxyHandler(SimpleHTTPProxyHandler):
    def request_handler(self, req, reqbody):
        m = re.match(r'https?://[^/]*google-analytics\.com/', req.path)
        if m:
            self.send_error(503)
            return True


if __name__ == '__main__':
    test(HandlerClass=DenyProxyHandler)
