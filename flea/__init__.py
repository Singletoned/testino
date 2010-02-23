from wsgiref.validate import validator as wsgi_validator
from cStringIO import StringIO
from urlparse import urlparse, urlunparse
from Cookie import BaseCookie
import re
from functools import wraps

from lxml.html import fromstring, tostring
from lxml.cssselect import CSSSelector

from pesto.testing import MockResponse
from pesto.request import Request
from pesto.wsgiutils import uri_join, make_query
from pesto.httputils import parse_querystring
from pesto.utils import MultiDict

xpath_registry = {}

class XPathMultiMethod(object):

    def __init__(self):
        self.endpoints = []

    def __call__(self, *args, **kwargs):
        el = args[0]
        el = getattr(el, 'element', el)
        for expr, func in self.endpoints:
            if el in el.xpath(expr):
                return func(*args, **kwargs)
        raise Exception("Couldn't find a match for element %r in %r" % (el, self.endpoints))

    def register(self, xpath, func):
        self.endpoints.append((xpath, func))

def when(xpath_expr):
    def when(func):
        if getattr(func, '__wrapped__', None):
            func = getattr(func, '__wrapped__')
        multimethod = xpath_registry.setdefault(func.__name__, XPathMultiMethod())
        multimethod.register(xpath_expr, func)
        wrapped = wraps(func)(
            lambda self, *args, **kwargs: multimethod(self, *args, **kwargs)
        )
        wrapped.__wrapped__ = func
        return wrapped
    return when

class ElementWrapper(object):

    def __init__(self, agent, element):
        self.agent = agent
        self.element = element

    def __str__(self):
        return str(self.element)

    def __repr__(self):
        return '<ElementWrapper %r>' % (self.element,)

    def __getattr__(self, attr):
        return getattr(self.element, attr)

    def __getitem__(self, xpath):

        try:
            element = self.element.xpath(xpath)[0]
        except IndexError:
            raise KeyError("xpath %r could not be located in %s" % (xpath, self))

        return self.__class__(self.agent, element)

    @when("//a[@href]")
    def click(self, follow=False):
        return self.agent._click(self, follow=follow)

    @when("//input[@type='checkbox']")
    def _get_value(self):
        return self.element.attrib.get('value', 'On')

    @when("//input")
    def _get_value(self):
        return self.element.attrib.get('value', '')

    @when("//input")
    def _set_value(self, value):
        self.element.attrib['value'] = value

    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return False
        return (
            self.element is other.element
            and self.agent is other.agent
        )

    #@when("//input[@type='radio']")
    #def _get_value(self):
    #    print "_get_value", self
    #    return list(
    #        item for item in (
    #            item.attrib.get('value', None)
    #            for item in self.form.xpath("//input[@type='radio' and @name=$name]", name=attrib['name'])
    #        ) if item is not None
    #    )

    #@when("//input[@type='radio']")
    #def _set_value(self):
    #    for item in self.form.xpath("//input[@type='radio' and @name=$name]", name=attrib['name']):
    #        if item.attrib['value'] == value:
    #            item.attrib['checked'] = 'checked'
    #        else:
    #            if 'checked' in item.attrib:
    #                del item.attrib['checked']

    value = property(_get_value, _set_value)

    @when("//input[@type='radio' or @type='checkbox']")
    def submit_value(self):
        if 'checked' in self.element.attrib:
            return self.value
        return None

    @when("//input[@type='text' or @type='password']")
    def submit_value(self):
        return self.value

    submit_value = property(submit_value)

    def _get_checked(self, value):
        return 'checked' in self.attrib

    def _set_checked(self, value):
        if bool(value):
            self.attrib['checked'] = 'checked'
        else:
            try:
                del self.attrib['checked']
            except KeyError:
                pass
    checked = property(_get_checked, _set_checked)



    @when("//input|textarea|button")
    def form(self):
        return self.__class__(self.agent, self.element.xpath("../form[1]")[0])

    @when("//form")
    def submit(self, follow=False):
        method = self.element.attrib['method'].upper()
        data = []
        for input in (ElementWrapper(self.agent, el) for el in self.element.xpath('.//input')):
            try:
                name = input.attrib['name']
            except KeyError:
                continue
            value = input.submit_value
            if value is None:
                continue
            elif isinstance(value, basestring):
                data.append((name, value))
            else:
                data += [(name, v) for v in value]
        path = self.element.attrib.get('action', self.agent.request.request_path)
        return {
            ('GET', None): self.agent.get,
            ('POST', None): self.agent.post,
            ('POST', 'multipart/form-data'): self.agent.post_multipart,
        }[(method, self.attrib.get('encoding'))](path, data, follow=follow)


    @when("//*")
    def submit(self, follow=False):
        self.xpath('.//ancestor::form[1]/').submit(follow=follow)

class ResultWrapper(list):

    def __init__(self, elements):
        super(ResultWrapper, self).__init__(elements)

    def __getattr__(self, attr):
        return getattr(self[0], attr)

    def __getitem__(self, item):
        if isinstance(item, int):
            return super(ResultWrapper, self).__getitem__(item)
        else:
            return self[0][item]

    def click(self, follow=False):
        return self[0].click(follow=follow)

    def _get_value(self):
        return self[0].value
    def _set_value(self, value):
        self[0].value = value
    value = property(_get_value, _set_value)

    def _get_checked(self):
        return self[0].checked
    def _set_checked(self, value):
        self[0].checked = checked
    checked = property(_get_checked, _set_checked)

class TestAgent(object):

    response_class = MockResponse
    _lxmldoc = None

    environ_defaults = {
        'SCRIPT_NAME': "",
        'PATH_INFO': "",
        'QUERY_STRING': "",
        'SERVER_NAME': "localhost",
        'SERVER_PORT': "80",
        'SERVER_PROTOCOL': "HTTP/1.0",
        'REMOTE_ADDR': '127.0.0.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'http',
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
    }

    def __init__(self, app, request=None, response=None, cookies=None, validate_wsgi=True):
        if validate_wsgi:
            app = wsgi_validator(app)
        self.app = app
        self.request = request
        self.response = response
        if cookies:
            self.cookies = cookies
        else:
            self.cookies = BaseCookie()
        if response:
            self.cookies.update(parse_cookies(response))

    @classmethod
    def make_environ(cls, REQUEST_METHOD='GET', PATH_INFO='', wsgi_input='', **kwargs):
        SCRIPT_NAME = kwargs.pop('SCRIPT_NAME', cls.environ_defaults["SCRIPT_NAME"])

        if SCRIPT_NAME and SCRIPT_NAME[-1] == "/":
            SCRIPT_NAME = SCRIPT_NAME[:-1]
            PATH_INFO = "/" + PATH_INFO

        environ = cls.environ_defaults.copy()
        environ.update(kwargs)
        for key, value in kwargs.items():
            environ[key.replace('wsgi_', 'wsgi.')] = value

        if isinstance(wsgi_input, basestring):
            wsgi_input = StringIO(wsgi_input)

        environ.update({
            'REQUEST_METHOD': REQUEST_METHOD,
            'SCRIPT_NAME': SCRIPT_NAME,
            'PATH_INFO': PATH_INFO,
            'wsgi.input': wsgi_input,
            'wsgi.errors': StringIO(),
        })

        if environ['SCRIPT_NAME'] == '/':
            environ['SCRIPT_NAME'] = ''
            environ['PATH_INFO'] = '/' + environ['PATH_INFO']

        while PATH_INFO.startswith('//'):
            PATH_INFO = PATH_INFO[1:]

        return environ

    def _request(self, environ, follow=False):
        path = environ['SCRIPT_NAME'] + environ['PATH_INFO']
        environ['HTTP_COOKIE'] = '; '.join(
            '%s=%s' % (key, morsel.value) 
            for key, morsel in self.cookies.items()
            if path.startswith(morsel['path'])
        )

        response = self.response_class.from_wsgi(self.app, environ, self.start_response)
        response = self.__class__(self.app, Request(environ), response, self.cookies, validate_wsgi=False)
        if follow:
            return follow_redirects(response)
        return response

    def get(self, PATH_INFO='/', data=None, charset='UTF-8', follow=False, **kwargs):
        """
        Make a GET request to the application and return the response.
        """
        if '?' in PATH_INFO:
            PATH_INFO, querystring = PATH_INFO.split('?', 1)
            if data is None:
                data = MultiDict()
            data.update(parse_querystring(querystring))

        if data is not None:
            kwargs.setdefault('QUERY_STRING', make_query(data, charset=charset))

        return self._request(
            self.make_environ('GET', PATH_INFO=PATH_INFO, **kwargs),
            follow
        )

    def start_response(self, status, headers, exc_info=None):
        pass

    def post(self, PATH_INFO='/', data=None, charset='UTF-8', follow=False, **kwargs):
        """
        Make a POST request to the application and return the response.
        """
        if data is None:
            data = []

        data = make_query(data, charset=charset)
        wsgi_input = StringIO(data)
        wsgi_input.seek(0)

        return self._request(
            self.make_environ(
                'POST', PATH_INFO=PATH_INFO,
                CONTENT_TYPE="application/x-www-form-urlencoded",
                CONTENT_LENGTH=str(len(data)),
                wsgi_input=wsgi_input,
                **kwargs
            ),
            follow,
        )

    def post_multipart(self, PATH_INFO='/', data=None, files=None, charset='UTF-8', follow=False, **kwargs):
        """
        Create a MockWSGI configured to post multipart/form-data to the given URI.

        This is usually used for mocking file uploads

        data
            dictionary of post data
        files
            list of ``(name, filename, content_type, data)`` tuples. ``data``
            may be either a byte string, iterator or file-like object.
        """

        boundary = '----------------------------------------BoUnDaRyVaLuE'
        if data is None:
            data = {}
        if files is None:
            files = []

        items = chain(
            (
                (
                    [
                        ('Content-Disposition',
                         'form-data; name="%s"' % (name,))
                    ],
                    data.encode(charset)
                ) for name, value in data
            ), (
                (
                    [
                        ('Content-Disposition',
                         'form-data; name="%s"; filename="%s"' % (name, fname)),
                        ('Content-Type', content_type)
                    ], data
                ) for name, fname, content_type, data in files
            )
        )
        post_data = StringIO()
        post_data.write('--' + boundary)
        for headers, data in items:
            post_data.write(CRLF)
            for name, value in headers:
                post_data.write('%s: %s%s' % (name, value, CRLF))
            post_data.write(CRLF)
            if hasattr(data, 'read'):
                copyfileobj(data, post_data)
            elif isinstance(data, str):
                post_data.write(data)
            else:
                for chunk in data:
                    post_data.write(chunk)
            post_data.write(CRLF)
            post_data.write('--' + boundary)
        post_data.write('--' + CRLF)
        length = post_data.tell()
        post_data.seek(0)
        kwargs.setdefault('CONTENT_LENGTH', str(length))
        return self._request(
            self.make_environ(
                'POST',
                PATH_INFO,
                CONTENT_TYPE='multipart/form-data; boundary=%s' % boundary,
                wsgi_input=post_data,
                **kwargs
            ),
            follow=follow,
        )

    @property
    def body(self):
        return self.response.body

    @property
    def lxmldoc(self):
        if self._lxmldoc is not None:
            return self._lxmldoc
        self._lxmldoc = fromstring(self.response.body)
        return self._lxmldoc

    def find(self, path, **kwargs):
        result = self.lxmldoc.xpath(path, **kwargs)
        if not isinstance(result, list):
            raise ValueError("XPath expression %r does not yield a list of elements" % path)
        return ResultWrapper(
            ElementWrapper(self, el) for el in result
        )

    __getitem__ = find

    def findcss(self, selector):
        """
        Return elements matching the given CSS Selector (see
        ``lxml.cssselect`` for documentation on the ``CSSSelector`` class.
        """
        selector = CSSSelector(selector)
        return ResultWrapper(
            ElementWrapper(self, el) for el in selector(self.lxmldoc)
        )

    def click(self, path, follow=False, **kwargs):
        return self.find(path, **kwargs).click(follow=follow)

    def _click(self, element, follow=False):
        return self.get(
            uri_join_same_server(self.request.request_uri, element.attrib['href']),
            follow=follow
        )

def follow_redirects(response):
    """
    If response has a 301 or 302 status code, fetch (GET) the redirect target, until a non-redirect code is received
    """
    while int(response.response.status.split()[0]) in (301, 302):
        response = response.get(
            uri_join_same_server(
                response.request.request_uri,
                response.response.get_header('Location')
            )
        )
    return response


def striptags(node):
    """
    Strip tags out of ``lxml.html`` document ``node``, just leaving behind
    text. Normalize all sequences of whitespace to a single space.

    Use this for simple text comparisons when testing for document content

    Example:
        >>> striptags(fromstring('the <span>foo</span> is <strong>b</strong>ar'))
        'the foo is bar'

    """
    def _striptags(node):
        if node.text:
            yield node.text
        for subnode in node:
            for text in _striptags(subnode):
                yield text
        if node.tail:
            yield node.tail
    return re.sub(r'\s\s*', ' ', ''.join(_striptags(node)))

def uri_join_same_server(baseuri, uri):
    """
    Join two uris which are on the same server. The resulting URI will have the
    protocol and netloc portions removed. If the resulting URI has a different
    protocol/netloc then a ``ValueError`` will be raised.

        >>> uri_join_same_server('http://localhost/foo', 'bar')
        '/bar'
        >>> uri_join_same_server('http://localhost/foo', 'http://localhost/bar')
        '/bar'
        >>> uri_join_same_server('http://localhost/foo', 'http://example.org/bar')
        Traceback (most recent call last):
          ...
        ValueError: URI links to another server: http://example.org/bar

    """
    uri = uri_join(baseuri, uri)
    uri = urlparse(uri)
    if urlparse(baseuri)[:2] != uri[:2]:
        raise ValueError("URI links to another server: %s" % (urlunparse(uri),))
    return urlunparse((None, None) + uri[2:])

def parse_cookies(response):
    """
    Return a ``Cookie.BaseCookie`` object populated from cookies parsed from
    the response object
    """
    base_cookie = BaseCookie()
    for item in response.get_headers('Set-Cookie'):
        base_cookie.load(item)
    return base_cookie


