#!/usr/bin/env python

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test
from threading import Lock
import os

class SaveImagesProxyHandler(SimpleHTTPProxyHandler):
    global_lock = Lock()

    def url2path(self, url):
        schema, _, urlpath = self.path.split('/', 2)
        fpath = schema + '/' + urlpath.split('?')[0]
        fdir, fname = os.path.split(fpath)
        if not fname:
            fname = 'index.html'
            fpath = os.path.join(fdir, fname)
        return fpath

    def save_handler(self, req, res, body):
        content_type = res.headers.get('Content-Type', '')
        if content_type.startswith('image/'):
            fpath = self.url2path(self.path)
            fdir = os.path.dirname(fpath)
            with self.global_lock:
                if not os.path.isdir(fdir):
                    os.makedirs(fdir)
                with open(fpath, 'wb') as f:
                    f.write(body)


if __name__ == '__main__':
    test(HandlerClass=SaveImagesProxyHandler)
