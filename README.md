# SimpleHTTPProxy

A Simple HTTP Proxy like Python's SimpleHTTPServer module.

Features:

- easy to use
- easy to customize
- runs fast with minimum footprint
- requires no external modules
- supports threading
- supports gzip decompression


## Usage

```
$ python SimpleHTTPProxy.py 8080
```

or like SimpleHTTPServer:

```
$ python -m SimpleHTTPProxy
```

When the argument is not given, SimpleHTTPProxy uses tcp/8080.


## Customize

To customize, derive `SimpleHTTPProxyHandler` class and override the handler methods.

Some examples are included:

- SaveImagesProxy: store all 'image/*' files on the current directory (by keeping their url hierarchy)
- ChangeUAProxy: replace 'User-Agent' header of the client requests
- HideRefererProxy: replace 'Referer' header of the client requests
- RemoveIframeProxy: remove all &lt;iframe&gt; elements from 'text/html' contents
- StripAmazonProxy: force redirect to 'http://www.amazon.co.jp/dp/$ASIN' style url

You can use these proxies just as SimpleHTTPProxy:

```
$ python -m SaveImagesProxy
```
