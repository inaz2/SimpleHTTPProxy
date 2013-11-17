#!/usr/bin/env python

from SSLStripProxy import SSLStripProxyHandler, test

class OffmousedownGoogleProxyHandler(SSLStripProxyHandler):
    def ssl_response_handler(self, req, reqbody, res, resbody):
        if req.path.startswith('https://www.google.com/search?'):
            return resbody.replace(' onmousedown="', ' onmousedown="return;')


if __name__ == '__main__':
    test(HandlerClass=OffmousedownGoogleProxyHandler)
