#!/usr/bin/env python

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test

class ShowHeadersProxyHandler(SimpleHTTPProxyHandler):
    version_table = {10: 'HTTP/1.0', 11: 'HTTP/1.1', 9: 'HTTP/0.9'}

    def save_handler(self, req, res, body):
        print '----'
        print req.requestline
        print req.headers
        print self.version_table[res.version], res.status, res.reason
        print res.headers


if __name__ == '__main__':
    test(HandlerClass=ShowHeadersProxyHandler)
