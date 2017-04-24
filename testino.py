# -*- coding: utf-8 -*-

import urllib.parse

import requests
import wsgiadapter
import lxml.html
from parsel.csstranslator import HTMLTranslator


class Agent(object):
    def __init__(self, wsgi_app, base_url="http://example.com/"):
        self.app = wsgi_app
        self.base_url = base_url
        self.session = requests.Session()
        self.session.hooks = {'response': Response}
        self.session.mount(
            self.base_url,
            wsgiadapter.WSGIAdapter(self.app))

    def get(self, url):
        url = urllib.parse.urljoin(self.base_url, url)
        return self.session.get(url)


class Response(object):
    def __init__(self, response, **kwargs):
        self.response = response

    def __getattr__(self, key):
        return getattr(self.response, key)

    def one(self, selector):
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
