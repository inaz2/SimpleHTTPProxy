#!/usr/bin/env python

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test

class ChangeUAProxyHandler(SimpleHTTPProxyHandler):
    def request_handler(self, req, reqbody):
        req.headers['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A403 Safari/8536.25'
        # req.headers['User-Agent'] = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'


if __name__ == '__main__':
    test(HandlerClass=ChangeUAProxyHandler)
