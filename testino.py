# -*- coding: utf-8 -*-

import urllib.parse

import requests
import wsgiadapter
import lxml.html
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
    def __init__(self, wsgi_app, base_url="http://example.com/"):
        super(WSGIAgent, self).__init__(base_url)
        self.app = wsgi_app
        self.session.mount(self.base_url, wsgiadapter.WSGIAdapter(self.app))


class Response(object):
    def __init__(self, response, agent):
        self.response = response
        self.agent = agent
        if self.mime_type == "text/html" and self.content:
            self.lxml = lxml.html.fromstring(self.content)
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

    def to_string(self):
        return lxml.html.tostring(self.lxml)

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
        if index is None:
            els = self.one(selector)
        else:
            els = self.all(selector)[index]
        url = els.attrib['href']
        return self.agent.get(url)

    def get_form(self, index=None):
        if index is not None:
            form = self.all("form")[index]
        else:
            try:
                form = self.one("form")
            except AssertionError:
                raise MissingFormError()
        return Form(self, form)

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
        self.element.fields[key] = str(value)

    def submit_data(self):
        return dict(self.element.form_values())

    def submit(self):
        data = self.submit_data()
        action = urllib.parse.urljoin(self.response.url, self.action)
        func = getattr(self.response.agent, self.method.lower())
        response = func(action, data=data)
        return response

    def to_string(self):
        return lxml.html.tostring(self.element)
