#!/usr/bin/env python

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test
import re

class ReplaceContentProxyHandler(SimpleHTTPProxyHandler):
    def response_handler(self, req, res, body):
        content_type = res.headers.get('Content-Type', '')
        if content_type.startswith('text/html'):
            return re.sub(r'<iframe[\s\S]+?</iframe>', '&lt;iframe removed&gt;', body)


if __name__ == '__main__':
    test(HandlerClass=ReplaceContentProxyHandler)
