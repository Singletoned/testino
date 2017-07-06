# -*- coding: utf-8 -*-

import urllib.parse

import requests
import wsgiadapter
import lxml.html
from parsel.csstranslator import HTMLTranslator
from werkzeug.http import parse_options_header


class XPath(str):
    pass


class BaseAgent(object):
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.hooks = {'response': self.make_response}

    def get(self, url, params=None):
        url = urllib.parse.urljoin(self.base_url, url)
        return self.session.get(url, params=params)

    def make_response(self, response, **kwargs):
        return Response(
            response=response,
            agent=self)


class WSGIAgent(BaseAgent):
    def __init__(self, wsgi_app, base_url="http://example.com/"):
        super(WSGIAgent, self).__init__(base_url)
        self.app = wsgi_app
        self.session.mount(
            self.base_url,
            wsgiadapter.WSGIAdapter(self.app))


class Response(object):
    def __init__(self, response, agent):
        self.response = response
        self.agent = agent
        self.lxml = lxml.html.fromstring(self.content)

    def __getattr__(self, key):
        return getattr(self.response, key)

    @property
    def path(self):
        return urllib.parse.urlparse(self.url).path

    @property
    def mime_type(self):
        return parse_options_header(self.headers['Content-Type'])[0]

    @property
    def charset(self):
        return parse_options_header(
            self.headers['Content-Type'])[1].get('charset', "")

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

    def get_form(self):
        return Form(self, self.one("form"))


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

    def __setitem__(self, key, value):
        css_path = "*[name='{}']".format(key)
        element = self.response.one(css_path)
        element.value = value

    def _submit_data(self):
        els = self.element.xpath(".//input")
        for el in els:
            name = el.attrib.get('name', '')
            value = el.attrib.get('value', '')
            yield (name, value)

    def submit_data(self):
        data = self._submit_data()
        data = dict((k,v) for (k,v) in data if k)
        return data

    def submit(self):
        data = self.submit_data()
        func = getattr(self.response.agent, self.method.lower())
        response = func(self.action, params=data)
        return response
