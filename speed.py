import csv
import datetime
import errno
import math
import os
import platform
import re
import signal
import socket
import sys
import threading
import timeit
import xml.parsers.expat

try:
    import gzip
    GZIP_BASE = gzip.GzipFile
except ImportError:
    gzip = None
    GZIP_BASE = object

__version__ = '2.1.4b1'


class FakeShutdownEvent(object):
    """Class to fake a threading.Event.isSet so that home of this module
    are not required to register their own threading.Event()
    """

    @staticmethod
    def isSet():
        "Dummy method to always return false"""
        return False

    is_set = isSet


# Some global variables we use
DEBUG = False
_GLOBAL_DEFAULT_TIMEOUT = object()
PY25PLUS = sys.version_info[:2] >= (2, 5)
PY26PLUS = sys.version_info[:2] >= (2, 6)
PY32PLUS = sys.version_info[:2] >= (3, 2)
PY310PLUS = sys.version_info[:2] >= (3, 10)

# Begin import game to handle Python 2 and Python 3
try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        json = None

try:
    import xml.etree.ElementTree as ET
    try:
        from xml.etree.ElementTree import _Element as ET_Element
    except ImportError:
        pass
except ImportError:
    from xml.dom import minidom as DOM
    from xml.parsers.expat import ExpatError
    ET = None

try:
    from urllib2 import (urlopen, Request, HTTPError, URLError,
                         AbstractHTTPHandler, ProxyHandler,
                         HTTPDefaultErrorHandler, HTTPRedirectHandler,
                         HTTPErrorProcessor, OpenerDirector)
except ImportError:
    from urllib.request import (urlopen, Request, HTTPError, URLError,
                                AbstractHTTPHandler, ProxyHandler,
                                HTTPDefaultErrorHandler, HTTPRedirectHandler,
                                HTTPErrorProcessor, OpenerDirector)

try:
    from httplib import HTTPConnection, BadStatusLine
except ImportError:
    from http.client import HTTPConnection, BadStatusLine

try:
    from httplib import HTTPSConnection
except ImportError:
    try:
        from http.client import HTTPSConnection
    except ImportError:
        HTTPSConnection = None

try:
    from httplib import FakeSocket
except ImportError:
    FakeSocket = None

try:
    from Queue import Queue
except ImportError:
    from queue import Queue

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

try:
    from urlparse import parse_qs
except ImportError:
    try:
        from urllib.parse import parse_qs
    except ImportError:
        from cgi import parse_qs

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

try:
    from argparse import ArgumentParser as ArgParser
    from argparse import SUPPRESS as ARG_SUPPRESS
    PARSER_TYPE_INT = int
    PARSER_TYPE_STR = str
    PARSER_TYPE_FLOAT = float
except ImportError:
    from optparse import OptionParser as ArgParser
    from optparse import SUPPRESS_HELP as ARG_SUPPRESS
    PARSER_TYPE_INT = 'int'
    PARSER_TYPE_STR = 'string'
    PARSER_TYPE_FLOAT = 'float'

try:
    from cStringIO import StringIO
    BytesIO = None
except ImportError:
    try:
        from StringIO import StringIO
        BytesIO = None
    except ImportError:
        from io import StringIO, BytesIO

try:
    import __builtin__
except ImportError:
    import builtins
    from io import TextIOWrapper, FileIO

    class _Py3Utf8Output(TextIOWrapper):
        """UTF-8 encoded wrapper around stdout for py3, to override
        ASCII stdout
        """
        def __init__(self, f, **kwargs):
            buf = FileIO(f.fileno(), 'w')
            super(_Py3Utf8Output, self).__init__(
                buf,
                encoding='utf8',
                errors='strict'
            )

        def write(self, s):
            super(_Py3Utf8Output, self).write(s)
            self.flush()

    _py3_print = getattr(builtins, 'print')
    try:
        _py3_utf8_stdout = _Py3Utf8Output(sys.stdout)
        _py3_utf8_stderr = _Py3Utf8Output(sys.stderr)
    except OSError:
        # sys.stdout/sys.stderr is not a compatible stdout/stderr object
        # just use it and hope things go ok
        _py3_utf8_stdout = sys.stdout
        _py3_utf8_stderr = sys.stderr

    def to_utf8(v):
        """No-op encode to utf-8 for py3"""
        return v

    def print_(*args, **kwargs):
        """Wrapper function for py3 to print, with a utf-8 encoded stdout"""
        if kwargs.get('file') == sys.stderr:
            kwargs['file'] = _py3_utf8_stderr
        else:
            kwargs['file'] = kwargs.get('file', _py3_utf8_stdout)
        _py3_print(*args, **kwargs)
else:
    del __builtin__

    def to_utf8(v):
        """Encode value to utf-8 if possible for py2"""
        try:
            return v.encode('utf8', 'strict')
        except AttributeError:
            return v

    def print_(*args, **kwargs):
        """The new-style print function for Python 2.4 and 2.5.

        Taken from https://pypi.python.org/pypi/six/

        Modified to set encoding to UTF-8 always, and to flush after write
        """
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return

        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            # If the file has an encoding, encode unicode with it.
            encoding = 'utf8'  # Always trust UTF-8 for output
            if (isinstance(fp, file) and
                    isinstance(data, unicode) and
                    encoding is not None):
                errors = getattr(fp, "errors", None)
                if errors is None:
                    errors = "strict"
                data = data.encode(encoding, errors)
            fp.write(data)
            fp.flush()
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

# Exception "constants" to support Python 2 through Python 3
try:
    import ssl
    try:
        CERT_ERROR = (ssl.CertificateError,)
    except AttributeError:
        CERT_ERROR = tuple()

    HTTP_ERRORS = (
        (HTTPError, URLError, socket.error, ssl.SSLError, BadStatusLine) +
        CERT_ERROR
    )
except ImportError:
    ssl = None
    HTTP_ERRORS = (HTTPError, URLError, socket.error, BadStatusLine)

if PY32PLUS:
    etree_iter = ET.Element.iter
elif PY25PLUS:
    etree_iter = ET_Element.getiterator

if PY26PLUS:
    thread_is_alive = threading.Thread.is_alive
else:
    thread_is_alive = threading.Thread.isAlive


def event_is_set(event):
    try:
        return event.is_set()
    except AttributeError:
        return event.isSet()


class SpeedtestException(Exception):
    """Base exception for this module"""


class SpeedtestCLIError(SpeedtestException):
    """Generic exception for raising errors during CLI operation"""


class SpeedtestHTTPError(SpeedtestException):
    """Base HTTP exception for this module"""


class SpeedtestConfigError(SpeedtestException):
    """Configuration XML is invalid"""


class SpeedtestServersError(SpeedtestException):
    """Servers XML is invalid"""


class ConfigRetrievalError(SpeedtestHTTPError):
    """Could not retrieve config.php"""


class ServersRetrievalError(SpeedtestHTTPError):
    """Could not retrieve speedtest-servers.php"""


class InvalidServerIDType(SpeedtestException):
    """Server ID used for filtering was not an integer"""


class NoMatchedServers(SpeedtestException):
    """No servers matched when filtering"""


class SpeedtestMiniConnectFailure(SpeedtestException):
    """Could not connect to the provided speedtest mini server"""


class InvalidSpeedtestMiniServer(SpeedtestException):
    """Server provided as a speedtest mini server does not actually appear
    to be a speedtest mini server
    """


class ShareResultsConnectFailure(SpeedtestException):
    """Could not connect to speedtest.net API to POST results"""


class ShareResultsSubmitFailure(SpeedtestException):
    """Unable to successfully POST results to speedtest.net API after
    connection
    """


class SpeedtestUploadTimeout(SpeedtestException):
    """testlength configuration reached during upload
    Used to ensure the upload halts when no additional data should be sent
    """


class SpeedtestBestServerFailure(SpeedtestException):
    """Unable to determine best server"""


class SpeedtestMissingBestServer(SpeedtestException):
    """get_best_server not called or not able to determine best server"""


def create_connection(address, timeout=_GLOBAL_DEFAULT_TIMEOUT,
                      source_address=None):
    """Connect to *address* and return the socket object.

    Convenience function.  Connect to *address* (a 2-tuple ``(host,
    port)``) and return the socket object.  Passing the optional
    *timeout* parameter will set the timeout on the socket instance
    before attempting to connect.  If no *timeout* is supplied, the
    global default timeout setting returned by :fun`getdefaulttimeout`
    is used.  If *source_address* is set it must be a tuple of (host, port)
    for the socket to bind as a source address before making the connection.
    An host of '' or port 0 tells the OS to use the default.

    Largely vendored from Python 2.7, modified to work with Python 2.4
    """

    host, port = address
    err = None
    for res in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
        af, socktype, proto, canonname, sa = res
        sock = None
        try:
            sock = socket.socket(af, socktype, proto)
            if timeout is not _GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(float(timeout))
            if source_address:
                sock.bind(source_address)
            sock.connect(sa)
            return sock

        except socket.error:
            err = get_exception()
            if sock is not None:
                sock.close()

    if err is not None:
        raise err
    else:
        raise socket.error("getaddrinfo returns an empty list")


class SpeedtestHTTPConnection(HTTPConnection):
    """Custom HTTPConnection to support source_address across
    Python 2.4 - Python 3
    """
    def __init__(self, *args, **kwargs):
        source_address = kwargs.pop('source_address', None)
        timeout = kwargs.pop('timeout', 10)

        self._tunnel_host = None

        HTTPConnection.__init__(self, *args, **kwargs)

        self.source_address = source_address
        self.timeout = timeout

    def connect(self):
        """Connect to the host and port specified in __init__."""
        try:
            self.sock = socket.create_connection(
                (self.host, self.port),
                self.timeout,
                self.source_address
            )
        except (AttributeError, TypeError):
            self.sock = create_connection(
                (self.host, self.port),
                self.timeout,
                self.source_address
            )

        if self._tunnel_host:
            self._tunnel()


if HTTPSConnection:
    class SpeedtestHTTPSConnection(HTTPSConnection):
        """Custom HTTPSConnection to support source_address across
        Python 2.4 - Python 3
        """
        default_port = 443

        def __init__(self, *args, **kwargs):
            source_address = kwargs.pop('source_address', None)
            timeout = kwargs.pop('timeout', 10)

            self._tunnel_host = None

            HTTPSConnection.__init__(self, *args, **kwargs)

            self.timeout = timeout
            self.source_address = source_address

        def connect(self):
            "Connect to a host on a given (SSL) port."
            try:
                self.sock = socket.create_connection(
                    (self.host, self.port),
                    self.timeout,
                    self.source_address
                )
            except (AttributeError, TypeError):
                self.sock = create_connection(
                    (self.host, self.port),
                    self.timeout,
                    self.source_address
                )

            if self._tunnel_host:
                self._tunnel()

            if ssl:
                try:
                    kwargs = {}
                    if hasattr(ssl, 'SSLContext'):
                        if self._tunnel_host:
                            kwargs['server_hostname'] = self._tunnel_host
                        else:
                            kwargs['server_hostname'] = self.host
                    self.sock = self._context.wrap_socket(self.sock, **kwargs)
                except AttributeError:
                    self.sock = ssl.wrap_socket(self.sock)
                    try:
                        self.sock.server_hostname = self.host
                    except AttributeError:
                        pass
            elif FakeSocket:
                # Python 2.4/2.5 support
                try:
                    self.sock = FakeSocket(self.sock, socket.ssl(self.sock))
                except AttributeError:
                    raise SpeedtestException(
                        'This version of Python does not support HTTPS/SSL '
                        'functionality'
                    )
            else:
                raise SpeedtestException(
                    'This version of Python does not support HTTPS/SSL '
                    'functionality'
                )


def _build_connection(connection, source_address, timeout, context=None):
    """Cross Python 2.4 - Python 3 callable to build an ``HTTPConnection`` or
    ``HTTPSConnection`` with the args we need

    Called from ``http(s)_open`` methods of ``SpeedtestHTTPHandler`` or
    ``SpeedtestHTTPSHandler``
    """
    def inner(host, **kwargs):
        kwargs.update({
            'source_address': source_address,
            'timeout': timeout
        })
        if context:
            kwargs['context'] = context
        return connection(host, **kwargs)
    return inner


class SpeedtestHTTPHandler(AbstractHTTPHandler):
    """Custom ``HTTPHandler`` that can build a ``HTTPConnection`` with the
    args we need for ``source_address`` and ``timeout``
    """
    def __init__(self, debuglevel=0, source_address=None, timeout=10):
        AbstractHTTPHandler.__init__(self, debuglevel)
        self.source_address = source_address
        self.timeout = timeout

    def http_open(self, req):
        return self.do_open(
            _build_connection(
                SpeedtestHTTPConnection,
                self.source_address,
                self.timeout
            ),
            req
        )

    http_request = AbstractHTTPHandler.do_request_


class SpeedtestHTTPSHandler(AbstractHTTPHandler):
    """Custom ``HTTPSHandler`` that can build a ``HTTPSConnection`` with the
    args we need for ``source_address`` and ``timeout``
    """
    def __init__(self, debuglevel=0, context=None, source_address=None,
                 timeout=10):
        AbstractHTTPHandler.__init__(self, debuglevel)
        self._context = context
        self.source_address = source_address
        self.timeout = timeout

    def https_open(self, req):
        return self.do_open(
            _build_connection(
                SpeedtestHTTPSConnection,
                self.source_address,
                self.timeout,
                context=self._context,
            ),
            req
        )

    https_request = AbstractHTTPHandler.do_request_


def build_opener(source_address=None, timeout=10):
    """Function similar to ``urllib2.build_opener`` that will build
    an ``OpenerDirector`` with the explicit handlers we want,
    ``source_address`` for binding, ``timeout`` and our custom
    `User-Agent`
    """

    printer('Timeout set to %d' % timeout, debug=True)

    if source_address:
        source_address_tuple = (source_address, 0)
        printer('Binding to source address: %r' % (source_address_tuple,),
                debug=True)
    else:
        source_address_tuple = None

    handlers = [
        ProxyHandler(),
        SpeedtestHTTPHandler(source_address=source_address_tuple,
                             timeout=timeout),
        SpeedtestHTTPSHandler(source_address=source_address_tuple,
                              timeout=timeout),
        HTTPDefaultErrorHandler(),
        HTTPRedirectHandler(),
        HTTPErrorProcessor()
    ]

    opener = OpenerDirector()
    opener.addheaders = [('User-agent', build_user_agent())]

    for handler in handlers:
        opener.add_handler(handler)

    return opener


class GzipDecodedResponse(GZIP_BASE):
    """A file-like object to decode a response encoded with the gzip
    method, as described in RFC 1952.

    Largely copied from ``xmlrpclib``/``xmlrpc.client`` and modified
    to work for py2.4-py3
    """
    def __init__(self, response):
        # response doesn't support tell() and read(), required by
        # GzipFile
        if not gzip:
            raise SpeedtestHTTPError('HTTP response body is gzip encoded, '
                                     'but gzip support is not available')
        IO = BytesIO or StringIO
        self.io = IO()
        while 1:
            chunk = response.read(1024)
            if len(chunk) == 0:
                break
            self.io.write(chunk)
        self.io.seek(0)
        gzip.GzipFile.__init__(self, mode='rb', fileobj=self.io)

    def close(self):
        try:
            gzip.GzipFile.close(self)
        finally:
            self.io.close()


def get_exception():
    """Helper function to work with py2.4-py3 for getting the current
    exception in a try/except block
    """
    return sys.exc_info()[1]


def distance(origin, destination):
    """Determine distance between 2 sets of [lat,lon] in km"""

    lat1, lon1 = origin
    lat2, lon2 = destination
    radius = 6371  # km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) * math.sin(dlon / 2) *
         math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = radius * c

    return d


def build_user_agent():
    """Build a Mozilla/5.0 compatible User-Agent string"""

    ua_tuple = (
        'Mozilla/5.0',
        '(%s; U; %s; en-us)' % (platform.platform(),
                                platform.architecture()[0]),
        'Python/%s' % platform.python_version(),
        '(KHTML, like Gecko)',
        'speedtest-cli/%s' % __version__
    )
    user_agent = ' '.join(ua_tuple)
    printer('User-Agent: %s' % user_agent, debug=True)
    return user_agent


def build_request(url, data=None, headers=None, bump='0', secure=False):
    """Build a urllib2 request object

    This function automatically adds a User-Agent header to all requests

    """

    if not headers:
        headers = {}

    if url[0] == ':':
        scheme = ('http', 'https')[bool(secure)]
        schemed_url = '%s%s' % (scheme, url)
    else:
        schemed_url = url

    if '?' in url:
        delim = '&'
    else:
        delim = '?'

    # WHO YOU GONNA CALL? CACHE BUSTERS!
    final_url = '%s%sx=%s.%s' % (schemed_url, delim,
                                 int(timeit.time.time() * 1000),
                                 bump)

    headers.update({
        'Cache-Control': 'no-cache',
    })

    printer('%s %s' % (('GET', 'POST')[bool(data)], final_url),
            debug=True)

    return Request(final_url, data=data, headers=headers)


def catch_request(request, opener=None):
    """Helper function to catch common exceptions encountered when
    establishing a connection with a HTTP/HTTPS request

    """

    if opener:
        _open = opener.open
    else:
        _open = urlopen

    try:
        uh = _open(request)
        if request.get_full_url() != uh.geturl():
            printer('Redirected to %s' % uh.geturl(), debug=True)
        return uh, False
    except HTTP_ERRORS:
        e = get_exception()
        return None, e


def get_response_stream(response):
    """Helper function to return either a Gzip reader if
    ``Content-Encoding`` is ``gzip`` otherwise the response itself

    """

    try:
        getheader = response.headers.getheader
    except AttributeError:
        getheader = response.getheader

    if getheader('content-encoding') == 'gzip':
        return GzipDecodedResponse(response)

    return response


def get_attributes_by_tag_name(dom, tag_name):
    """Retrieve an attribute from an XML document and return it in a
    consistent format

    Only used with xml.dom.minidom, which is likely only to be used
    with python versions older than 2.5
    """
    elem = dom.getElementsByTagName(tag_name)[0]
    return dict(list(elem.attributes.items()))


def print_dots(shutdown_event):
    """Built in callback function used by Thread classes for printing
    status
    """
    def inner(current, total, start=False, end=False):
        if event_is_set(shutdown_event):
            return

        sys.stdout.write('.')
        if current + 1 == total and end is True:
            sys.stdout.write('\n')
        sys.stdout.flush()
    return inner


def do_nothing(*args, **kwargs):
    pass


class HTTPDownloader(threading.Thread):
    """Thread class for retrieving a URL"""

    def __init__(self, i, request, start, timeout, opener=None,
                 shutdown_event=None):
        threading.Thread.__init__(self)
        self.request = request
        self.result = [0]
        self.starttime = start
        self.timeout = timeout
        self.i = i
        if opener:
            self._opener = opener.open
        else:
            self._opener = urlopen

        if shutdown_event:
            self._shutdown_event = shutdown_event
        else:
            self._shutdown_event = FakeShutdownEvent()

    def run(self):
        try:
            if (timeit.default_timer() - self.starttime) <= self.timeout:
                f = self._opener(self.request)
                while (not event_is_set(self._shutdown_event) and
                        (timeit.default_timer() - self.starttime) <=
                        self.timeout):
                    self.result.append(len(f.read(10240)))
                    if self.result[-1] == 0:
                        break
                f.close()
        except IOError:
            pass
        except HTTP_ERRORS:
            pass


class HTTPUploaderData(object):
    """File like object to improve cutting off the upload once the timeout
    has been reached
    """

    def __init__(self, length, start, timeout, shutdown_event=None):
        self.length = length
        self.start = start
        self.timeout = timeout

        if shutdown_event:
            self._shutdown_event = shutdown_event
        else:
            self._shutdown_event = FakeShutdownEvent()

        self._data = None

        self.total = [0]

    def pre_allocate(self):
        chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        multiplier = int(round(int(self.length) / 36.0))
        IO = BytesIO or StringIO
        try:
            self._data = IO(
                ('content1=%s' %
                 (chars * multiplier)[0:int(self.length) - 9]
                 ).encode()
            )
        except MemoryError:
            raise SpeedtestCLIError(
                'Insufficient memory to pre-allocate upload data. Please '
                'use --no-pre-allocate'
            )

    @property
    def data(self):
        if not self._data:
            self.pre_allocate()
        return self._data

    def read(self, n=10240):
        if ((timeit.default_timer() - self.start) <= self.timeout and
                not event_is_set(self._shutdown_event)):
            chunk = self.data.read(n)
            self.total.append(len(chunk))
            return chunk
        else:
            raise SpeedtestUploadTimeout()

    def __len__(self):
        return self.length


class HTTPUploader(threading.Thread):
    """Thread class for putting a URL"""

    def __init__(self, i, request, start, size, timeout, opener=None,
                 shutdown_event=None):
        threading.Thread.__init__(self)
        self.request = request
        self.request.data.start = self.starttime = start
        self.size = size
        self.result = 0
        self.timeout = timeout
        self.i = i

        if opener:
            self._opener = opener.open
        else:
            self._opener = urlopen

        if shutdown_event:
            self._shutdown_event = shutdown_event
        else:
            self._shutdown_event = FakeShutdownEvent()

    def run(self):
        request = self.request
        try:
            if ((timeit.default_timer() - self.starttime) <= self.timeout and
                    not event_is_set(self._shutdown_event)):
                try:
                    f = self._opener(request)
                except TypeError:
                    # PY24 expects a string or buffer
                    # This also causes issues with Ctrl-C, but we will concede
                    # for the moment that Ctrl-C on PY24 isn't immediate
                    request = build_request(self.request.get_full_url(),
                                            data=request.data.read(self.size))
                    f = self._opener(request)
                f.read(11)
                f.close()
                self.result = sum(self.request.data.total)
            else:
                self.result = 0
        except (IOError, SpeedtestUploadTimeout):
            self.result = sum(self.request.data.total)
        except HTTP_ERRORS:
            self.result = 0


class SpeedtestResults(object):
    """Class for holding the results of a speedtest, including:

    Download speed
    Upload speed
    Ping/Latency to test server
    Data about server that the test was run against

    Additionally this class can return a result data as a dictionary or CSV,
    as well as submit a POST of the result data to the speedtest.net API
    to get a share results image link.
    """

    def __init__(self, download=0, upload=0, ping=0, server=None, client=None,
                 opener=None, secure=False):
        self.download = download
        self.upload = upload
        self.ping = ping
        if server is None:
            self.server = {}
        else:
            self.server = server
        self.client = client or {}

        self._share = None
        self.timestamp = '%sZ' % datetime.datetime.utcnow().isoformat()
        self.bytes_received = 0
        self.bytes_sent = 0

        if opener:
            self._opener = opener
        else:
            self._opener = build_opener()

        self._secure = secure

    def __repr__(self):
        return repr(self.dict())

    def share(self):
        """POST data to the speedtest.net API to obtain a share results
        link
        """

        if self._share:
            return self._share

        download = int(round(self.download / 1000.0, 0))
        ping = int(round(self.ping, 0))
        upload = int(round(self.upload / 1000.0, 0))

        # Build the request to send results back to speedtest.net
        # We use a list instead of a dict because the API expects parameters
        # in a certain order
        api_data = [
            'recommendedserverid=%s' % self.server['id'],
            'ping=%s' % ping,
            'screenresolution=',
            'promo=',
            'download=%s' % download,
            'screendpi=',
            'upload=%s' % upload,
            'testmethod=http',
            'hash=%s' % md5(('%s-%s-%s-%s' %
                             (ping, upload, download, '297aae72'))
                            .encode()).hexdigest(),
            'touchscreen=none',
            'startmode=pingselect',
            'accuracy=1',
            'bytesreceived=%s' % self.bytes_received,
            'bytessent=%s' % self.bytes_sent,
            'serverid=%s' % self.server['id'],
        ]

        headers = {'Referer': 'http://c.speedtest.net/flash/speedtest.swf'}
        request = build_request('://www.speedtest.net/api/api.php',
                                data='&'.join(api_data).encode(),
                                headers=headers, secure=self._secure)
        f, e = catch_request(request, opener=self._opener)
        if e:
            raise ShareResultsConnectFailure(e)

        response = f.read()
        code = f.code
        f.close()

        if int(code) != 200:
            raise ShareResultsSubmitFailure('Could not submit results to '
                                            'speedtest.net')

        qsargs = parse_qs(response.decode())
        resultid = qsargs.get('resultid')
        if not resultid or len(resultid) != 1:
            raise ShareResultsSubmitFailure('Could not submit results to '
                                            'speedtest.net')

        self._share = 'http://www.speedtest.net/result/%s.png' % resultid[0]

        return self._share

    def dict(self):
        """Return dictionary of result data"""

        return {
            'download': self.download,
            'upload': self.upload,
            'ping': self.ping,
            'server': self.server,
            'timestamp': self.timestamp,