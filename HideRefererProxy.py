#!/usr/bin/env python

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test

class HideRefererProxyHandler(SimpleHTTPProxyHandler):
    def request_handler(self):
        self.headers['Referer'] = self.path
        # del self.headers['Referer']


if __name__ == '__main__':
    test(HandlerClass=HideRefererProxyHandler)
