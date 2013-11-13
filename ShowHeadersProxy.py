#!/usr/bin/env python

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test
import sys

class ShowHeadersProxyHandler(SimpleHTTPProxyHandler):
    version_table = {10: 'HTTP/1.0', 11: 'HTTP/1.1', 9: 'HTTP/0.9'}

    def save_handler(self, req, res, body):
        text = """----
%s
%s
%s %d %s
%s
""" % (req.requestline, str(req.headers), self.version_table[res.version], res.status, res.reason, str(res.headers))
        print text.replace('\n', '\x1bE')    # use NEL control character for line break (useful for grep)
        sys.stdout.flush()


if __name__ == '__main__':
    test(HandlerClass=ShowHeadersProxyHandler)
