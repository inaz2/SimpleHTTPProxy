#!/usr/bin/env python
# -*- coding: utf-8 -*-

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test
import socket

class SendSSTPProxyHandler(SimpleHTTPProxyHandler):
    version_table = {10: 'HTTP/1.0', 11: 'HTTP/1.1', 9: 'HTTP/0.9'}

    def save_handler(self, req, reqbody, res, resbody):
        reqmsg = r"%s\nReferer: %s" % (req.requestline, req.headers.get('Referer', ''))
        resmsg = r"%s %d %s\nContent-Type: %s\nContent-Encoding: %s\nContent-Length: %s" % (self.version_table[res.version], res.status, res.reason, res.headers.get('Content-Type', ''), res.headers.get('Content-Encoding', ''), res.headers.get('Content-Length', ''))

        s = socket.create_connection(('localhost', 9801))
        text = r"""SEND SSTP/1.1
Sender: SendSSTPProxy
Script: \v\_q\h\s0%s\u%s\e
Option: nodescript,notranslate
Charset: UTF-8
""" % (reqmsg, resmsg)
        s.sendall(text.replace("\n", "\r\n"))
        s.close()


if __name__ == '__main__':
    test(HandlerClass=SendSSTPProxyHandler)
