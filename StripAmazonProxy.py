#!/usr/bin/env python

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test
import re

class StripAmazonProxyHandler(SimpleHTTPProxyHandler):
    def request_handler(self, req, reqbody):
        m = re.match(r'http://www\.amazon\.co\.jp/.+?/dp/([A-Z0-9]{10})', req.path)
        if m:
            redirect_url = "http://www.amazon.co.jp/dp/%s" % m.group(1)
            if req.path == redirect_url:
                return

            self.send_response(302)
            self.send_header('Location', redirect_url)
            self.send_header('Connection', 'close')
            self.end_headers()
            return True


if __name__ == '__main__':
    test(HandlerClass=StripAmazonProxyHandler)
