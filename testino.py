# -*- coding: utf-8 -*-

import urllib.parse
import difflib
import asyncio

import requests
import httpx
import wsgiadapter
import lxml.html
from lxml.html import builder as E
from parsel.csstranslator import HTMLTranslator
from werkzeug.http import parse_options_header


class MissingFieldError(Exception):
    def __init__(self, field_name):
        self.field_name = field_name

    def __str__(self):
        return "MissingFieldError: Field {} cannot be found".format(
            self.field_name
        )


class MissingFormError(Exception):
    def __str__(self):
        return "MissingFormError: No form found on the page"


class NotFound(Exception):
    def __init__(self, response):
        self.response = response

    def __str__(self):
        return "{} returned a 404".format(self.response)


class MethodNotAllowed(Exception):
    def __init__(self, response):
        self.response = response

    def __str__(self):
        return "{} returned a 405".format(self.response)


def print_quick_pprint_diff(item1, item2):
    if isinstance(item1, bytes):
        item1 = item1.decode("utf-8")
    if isinstance(item2, bytes):
        item2 = item2.decode("utf-8")
    diff = difflib.unified_diff(item1.split('\n'), item2.split('\n'))
    for line in list(diff):
        print(line)


def parse_html(html, strict=False):
    result = lxml.html.fromstring(html)
    if strict:
        output = lxml.html.tostring(result).decode("utf-8")
        try:
            assert output.strip() == html.strip()
        except AssertionError:
            print_quick_pprint_diff(html, output)
            raise
    return result


class XPath(str):
    pass


class BaseAgent(object):
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.hooks = {'response': self.make_response}

    def get(self, url, data=None, **kwargs):
        url = urllib.parse.urljoin(self.base_url, url)
        response = self.session.get(
            url, params=data, allow_redirects=False, **kwargs
        )
        if response.status_code == 404:
            raise NotFound(response)
        return response

    def post(self, url, data=None, **kwargs):
        url = urllib.parse.urljoin(self.base_url, url)
        response = self.session.post(
            url, data=data, allow_redirects=False, **kwargs
        )
        if response.status_code == 405:
            raise MethodNotAllowed(response)
        return response

    def make_response(self, response, **kwargs):
        return Response(response=response, agent=self)


class WSGIAgent(BaseAgent):
    def __init__(self, wsgi_app, base_url="http://example.com/", strict=False):
        super(WSGIAgent, self).__init__(base_url)
        self.app = wsgi_app
        self.session.mount(self.base_url, wsgiadapter.WSGIAdapter(self.app))
        self.strict = strict


def _sync(coroutine):
    return asyncio.get_event_loop().run_until_complete(coroutine)


class ASGIAgent():
    def __init__(self, app, base_url="http://example.com/"):
        self.client = httpx.AsyncClient(app=app)
        self.base_url = base_url

    def __getattr__(self, attr):
        response = getattr(self.client, attr)
        return response

    def get(self, url, *args, **kwargs):
        url = urllib.parse.urljoin(self.base_url, url)
        response = _sync(self.client.get(url, *args, **kwargs))
        return Response(response=response, agent=self)


class Response(object):
    def __init__(self, response, agent):
        self.response = response
        self.agent = agent
        self.strict = getattr(agent, 'strict', False)
        if self.mime_type == "text/html" and self.content:
            self.lxml = parse_html(self.content, strict=self.strict)
        else:
            self.lxml = None

    def __getattr__(self, key):
        return getattr(self.response, key)

    def __repr__(self):
        return "<Request {} {}>".format(self.status_code, self.path)

    @property
    def path(self):
        return urllib.parse.urlparse(self.url).path

    @property
    def mime_type(self):
        content_type = self.headers.get('Content-Type')
        if content_type:
            return parse_options_header(content_type)[0]

    @property
    def charset(self):
        return parse_options_header(self.headers['Content-Type'])[1].get(
            'charset', ""
        )

    def to_string(self, charset=None):
        if not charset:
            charset = self.charset
        return lxml.html.tostring(self.lxml).decode(charset)

    def one(self, selector):
        if not isinstance(selector, XPath):
            selector = HTMLTranslator().css_to_xpath(selector)
        els = self.lxml.xpath(selector)
        assert len(els) == 1, "Length is {}".format(len(els))
        return els[0]

    def has_one(self, selector):
        selector = HTMLTranslator().css_to_xpath(selector)
        els = self.lxml.xpath(selector)
        return len(els) == 1

    def has_text(self, text):
        selector = "*:contains({})".format(repr(text))
        selector = HTMLTranslator().css_to_xpath(selector)
        els = self.lxml.xpath(selector)
        return len(els) > 0

    def all(self, selector):
        selector = HTMLTranslator().css_to_xpath(selector)
        els = self.lxml.xpath(selector)
        return tuple(els)

    def click(self, selector=None, contains=None, index=None):
        if contains:
            selector = "a:contains('{}')".format(contains)
        els = self.all(selector)
        if index is None:
            assert len(els) > 0, "No matching links"
            assert len(els) < 2, "Too many matching links"
            index = 0
        el = els[index]
        url = el.attrib['href']
        return self.agent.get(url)

    def get_form(self, selector="form", index=None):
        els = self.all(selector)
        if index is None:
            assert len(els) > 0, "No matching forms"
            assert len(els) < 2, "Too many matching forms"
            index = 0
        el = els[index]
        return Form(self, el)

    def follow(self):
        assert 300 <= self.status_code < 400, self.status_code
        location = self.headers['Location']
        response = self.agent.get(location)
        return response


class Form(object):
    def __init__(self, response, element):
        self.response = response
        self.element = element

    @property
    def method(self):
        return self.element.attrib.get('method', 'GET').upper()

    @property
    def action(self):
        return self.element.attrib.get('action')

    def __getitem__(self, key):
        return self.element.fields[key]

    def __setitem__(self, key, value):
        if isinstance(value, int):
            value = str(value)
        self.element.fields[key] = value

    def check(self, label):
        selector = "label:contains({})".format(repr(label))
        label_els = self.element.cssselect(selector)
        assert len(label_els) == 1
        label_el = label_els[0]
        if label_el.for_element is not None:
            el = label_el.for_element
        else:
            el = label_el.cssselect("input")[0]
        el.checked = not el.checked

    def select(self, field_name, value, force=False):
        field = self.element.cssselect('''select[name={}]'''.format(field_name))[0]
        if not value in field.value_options:
            field.append(
                E.OPTION(value=str(value))
            )
        self[field_name] = value

    def set(self, field_name, value):
        if field_name in self.element.fields:
            self[field_name] = value
        else:
            self.element.append(
                E.INPUT(type="hidden", name=field_name, value=str(value))
            )

    def submit_data(self):
        data = dict(self.element.form_values())
        for field in self.element.inputs:
            if (field.attrib.get('type') == 'submit') and field.attrib.get('name'):
                data[field.attrib['name']] = field.value
        return data

    def submit(self, data=None, extra=None):
        if data is None:
            data = self.submit_data()
        if extra:
            data.update(extra)
        action = urllib.parse.urljoin(self.response.url, self.action)
        func = getattr(self.response.agent, self.method.lower())
        response = func(action, data=data)
        return response

    def to_string(self, charset=None):
        if not charset:
            charset = self.response.charset
        if self.element:
            return lxml.html.tostring(self.element).decode('ascii')
        else:
            return None
