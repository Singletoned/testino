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

    def get(self, url):
        url = urllib.parse.urljoin(self.base_url, url)
        return self.session.get(url)

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

    def one(self, selector):
        if not isinstance(selector, XPath):
            selector = HTMLTranslator().css_to_xpath(selector)
        els = lxml.html.fromstring(self.content).xpath(selector)
        assert len(els) == 1, "Length is {}".format(len(els))
        return els[0]

    def has_one(self, selector):
        selector = HTMLTranslator().css_to_xpath(selector)
        els = lxml.html.fromstring(self.content).xpath(selector)
        return len(els) == 1

    def has_text(self, text):
        selector = "*:contains({})".format(repr(text))
        selector = HTMLTranslator().css_to_xpath(selector)
        els = lxml.html.fromstring(self.content).xpath(selector)
        return len(els) > 0

    def all(self, selector):
        selector = HTMLTranslator().css_to_xpath(selector)
        els = lxml.html.fromstring(self.content).xpath(selector)
        return els

    def click(self, selector=None, contains=None, index=None):
        if contains:
            selector = "a:contains('{}')".format(contains)
        if index is None:
            els = self.one(selector)
        else:
            els = self.all(selector)[index]
        url = els.attrib['href']
        return self.agent.get(url)
