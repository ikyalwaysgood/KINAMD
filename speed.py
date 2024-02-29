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