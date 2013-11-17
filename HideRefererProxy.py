#!/usr/bin/env python

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test

class HideRefererProxyHandler(SimpleHTTPProxyHandler):
    def request_handler(self, req, reqbody):
        req.headers['Referer'] = req.path
        # del req.headers['Referer']


if __name__ == '__main__':
    test(HandlerClass=HideRefererProxyHandler)
