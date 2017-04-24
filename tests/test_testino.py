# -*- coding: utf-8 -*-

import unittest.mock

import nose
import pyjade

from testino import Response, XPath


document = pyjade.simple_convert('''
html
  body
    div#foo
      p This is foo
    div#bar
      p This is bar
    a#bumble(href="/bumble")
      button Bumble
    a#famble(href="/famble")
      button Famble
''')


class StubResponse(object):
    def __init__(self, content):
        self.content = content


class TestResponse(unittest.TestCase):
    def setUp(self):
        self.mock_agent = unittest.mock.Mock()
        self.response = Response(StubResponse(document), agent=self.mock_agent)

    def test_one(self):
        el = self.response.one("div#foo")
        assert el.text_content().strip() == "This is foo"

    def test_one_fails(self):
        with nose.tools.assert_raises(AssertionError):
            self.response.one("div#fumble")

    def test_one_xpath(self):
        el = self.response.one(XPath("//div[@id='foo']"))
        assert el.text_content().strip() == "This is foo"

    def test_one_fails_xpath(self):
        with nose.tools.assert_raises(AssertionError):
            self.response.one(XPath("//div[@id='fumble']"))

    def test_has_one(self):
        assert self.response.has_one("div#foo")

    def test_has_one_fails(self):
        assert not self.response.has_one("div#fumble")

    def test_all(self):
        els = self.response.all("div")
        assert len(els) == 2

    def test_has_text(self):
        assert self.response.has_text("This is foo")

    def test_has_text_fails(self):
        assert not self.response.has_text("Say hello to Mr Flibble")

    def test_click_contains(self):
        self.response.click(contains="Bumble")
        expected_calls = [unittest.mock.call.get('/bumble')]
        assert self.mock_agent.mock_calls == expected_calls

    def test_click_id(self):
        self.response.click("#bumble")
        expected_calls = [unittest.mock.call.get('/bumble')]
        assert self.mock_agent.mock_calls == expected_calls
