# SimpleHTTPProxy

A Simple HTTP Proxy like Python's SimpleHTTPServer module.

Features:

- easy to use
- easy to customize
- runs fast with minimum footprint
- requires no external modules
- HTTP/1.1 compliant to some extent
- supports IPv6 (for listening you need to edit the script)
- supports threading
- supports gzip compression
- supports sslstrip feature (by SSLStripProxy)


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

To customize, inherit `SimpleHTTPProxyHandler` class and override the handler methods.

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


## sslstripping by SSLStripProxy

SSLStripProxy inherits SimpleHTTPProxy and implements [sslstrip](http://www.thoughtcrime.org/software/sslstrip/)-like feature.

- work as HTTP proxy (not HTTPS)
- replace https urls to http ones in the responses and remember them
- forward client's HTTP requests to upstream servers as HTTPS requests

Also an example is included:

- OffmousedownGoogleProxy: disable onmousedown URL rewriting in Google's Result Pages (HTTPS)
- SSLSniffPasswordProxy: output POST parameters for login pages to stdout (also works via HTTP)

"HTTP Strict Transport Security" policies [RFC 6797] make the browsers always use HTTPS for its domain, so this proxy doesn't work for such cases.
