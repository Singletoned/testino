# -*- coding: utf-8 -*-

import unittest.mock

import nose
import pyjade

from testino import Response, WSGIAgent, MissingFieldError


form_document = pyjade.simple_convert('''
html
  body
    form(action="/result_page")
      input(name="flibble")
      input(type="text", name="text_field")
      select(name="select_field")
        option(value="1") One
        option(value="2") Two
''')


def wsgi_app(env, start_response):
    start_response('200 OK', [('Content-Type', 'text/html')])
    return [b"This is a WSGI app"]


class StubResponse(object):
    def __init__(self, content):
        self.content = content
        self.url = "http://example.com/flibble"
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.status_code = 999


class TestForm(unittest.TestCase):
    def setUp(self):
        self.agent = WSGIAgent(wsgi_app)
        self.response = Response(
            StubResponse(form_document), agent=self.agent)

    def test_input(self):
        form = self.response.get_form()
        form['flibble'] = "flamble"
        assert self.response.has_one("input[value='flamble']")

    def test_submit_data(self):
        form = self.response.get_form()
        form['flibble'] = "flamble"
        result = form.submit_data()
        expected = {
            'select_field': "",
            'flibble': "flamble",
            'text_field': ""}
        assert result == expected

    def test_submit(self):
        form = self.response.get_form()
        form['flibble'] = "flamble"
        expected_path = form.action
        page = form.submit()
        assert page.path == expected_path

    def test_non_string_value(self):
        form = self.response.get_form()
        form['flibble'] = 1

    def test_missing_field(self):
        form = self.response.get_form()
        with nose.tools.assert_raises(MissingFieldError) as e:
            form['_xyz_'] = "foo"
        expected_error = "MissingFieldError: Field _xyz_ cannot be found"
        assert str(e.exception) == expected_error

    def test_set_radio(self):
        form = self.response.get_form()
        form['select_field'] = "2"
        result = form.submit_data()
        expected = {
            'select_field': "2",
            'flibble': "",
            'text_field': ""}
        assert result == expected
