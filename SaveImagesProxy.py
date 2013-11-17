#!/usr/bin/env python

from SimpleHTTPProxy import SimpleHTTPProxyHandler, test
import os

class SaveImagesProxyHandler(SimpleHTTPProxyHandler):
    def url2path(self, url):
        schema, _, urlpath = self.path.split('/', 2)
        fpath = "SaveImagesProxy/%s/%s" % (schema.rstrip(':'), urlpath.split('?')[0])
        fdir, fname = os.path.split(fpath)
        if not fname:
            fname = 'index.html'
            fpath = os.path.join(fdir, fname)
        return fpath

    def save_handler(self, req, reqbody, res, resbody):
        content_type = res.headers.get('Content-Type', '')
        if content_type.startswith('image/'):
            fpath = self.url2path(self.path)
            fdir = os.path.dirname(fpath)
            if not os.path.isdir(fdir):
                os.makedirs(fdir)
            with open(fpath, 'wb') as f:
                f.write(resbody)


if __name__ == '__main__':
    test(HandlerClass=SaveImagesProxyHandler)
