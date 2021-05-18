# -*- coding: utf-8 -*-

import unittest.mock

import nose
import pyjade
import requests_mock

from testino import Response, XPath, WSGIAgent, BaseAgent, MissingFieldError, MissingFormError

document = pyjade.simple_convert(
    '''
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

form_document = pyjade.simple_convert(
    '''
html
  body
    form#one(action="/result_page_1")
      input(name="flibble_1")
    form#two(action="/result_page_2")
      input(name="flibble_2")
''')


def wsgi_app(env, start_response):
    start_response('200 OK', [('Content-Type', 'text/html')])
    return [b"This is a WSGI app"]


def test_WSGIAgent():
    agent = WSGIAgent(wsgi_app)
    response = agent.get("/")
    assert response.content == b"This is a WSGI app"


@requests_mock.mock()
def test_BaseAgent(mock_requests):
    mock_requests.get("http://example.com/foo", text='This is not a WSGI app')
    agent = BaseAgent("http://example.com")
    response = agent.get("/foo")
    assert response.content == b"This is not a WSGI app"


@requests_mock.mock()
def test_headers(mock_requests):
    mock_requests.get("http://example.com/foo", text='This is not a WSGI app')
    agent = BaseAgent("http://example.com")
    agent.get("/foo", headers={"Foo": "Bar"})
    assert mock_requests.request_history[0].headers['Foo'] == 'Bar'


class StubResponse(object):
    def __init__(self, content):
        self.content = content
        self.url = "http://example.com/flibble"
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.status_code = 999


class TestResponse(unittest.TestCase):
    def setUp(self):
        self.mock_agent = unittest.mock.Mock()
        self.mock_agent.strict = False
        self.response = Response(
            StubResponse(document), agent=self.mock_agent)

    def test_repr(self):
        assert str(self.response) == "<Request 999 /flibble>"

    def test_path(self):
        path = self.response.path
        assert path == "/flibble"

    def test_mime_type(self):
        assert self.response.mime_type == "text/html"

    def test_charset(self):
        assert self.response.charset == "utf-8"

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
        assert isinstance(els, tuple)

    def test_has_text(self):
        assert self.response.has_text("This is foo")

    def test_has_text_fails(self):
        assert not self.response.has_text("Say hello to Mr Flibble")

    def test_click_contains(self):
        self.response.click(contains="Bumble")
        expected_calls = [unittest.mock.call.get('/bumble')]
        assert self.mock_agent.mock_calls == expected_calls

    def test_click_contains_index(self):
        self.response.click(contains="ble", index=1)
        expected_calls = [unittest.mock.call.get('/famble')]
        assert self.mock_agent.mock_calls == expected_calls

    def test_click_id(self):
        self.response.click("#bumble")
        expected_calls = [unittest.mock.call.get('/bumble')]
        assert self.mock_agent.mock_calls == expected_calls

    def test_click_no_links(self):
        with nose.tools.assert_raises(AssertionError) as e:
            self.response.click(contains="FlubNuts")
        expected_error = "No matching links"
        assert str(e.exception) == expected_error, e.exception

    def test_click_too_many_links(self):
        with nose.tools.assert_raises(AssertionError) as e:
            self.response.click(contains="ble")
        expected_error = "Too many matching links"
        assert str(e.exception) == expected_error, e.exception

    def test_get_form_no_form(self):
        with nose.tools.assert_raises(AssertionError) as e:
            self.response.get_form()
        expected_error = "No matching forms"
        assert str(e.exception) == expected_error, e.exception

    def test_get_from_too_many_forms(self):
        response = Response(StubResponse(form_document), agent=self.mock_agent)
        with nose.tools.assert_raises(AssertionError) as e:
            response.get_form()
        expected_error = "Too many matching forms"
        assert str(e.exception) == expected_error, e.exception
