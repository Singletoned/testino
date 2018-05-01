# -*- coding: utf-8 -*-

import unittest.mock

import nose
import pyjade

from testino import Response, WSGIAgent


form_document = pyjade.simple_convert('''
html
  body
    form(action="./result_page")
      input(name="flibble")
      input(type="text", name="text_field")
      select(name="select_field")
        option(value="1") One
        option(value="2") Two
      input(type="radio", name="radio_field", value="a")
      input(type="radio", name="radio_field", value="b")
''')


two_form_document = pyjade.simple_convert('''
html
  body
    form(action="/result_page")
      input(name="flibble")
    form(action="/other_page")
      input(name="other_flibble")
''')


def wsgi_app(env, start_response):
    start_response('200 OK', [('Content-Type', 'text/html')])
    return [b"This is a WSGI app"]


class StubResponse(object):
    def __init__(self, content):
        self.content = content
        self.url = "http://example.com/flibble/"
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
        assert form['flibble'] == "flamble"

    def test_submit_data(self):
        form = self.response.get_form()
        form['flibble'] = "flamble"
        result = form.submit_data()
        assert result['flibble'] == "flamble"

    def test_submit(self):
        form = self.response.get_form()
        form['flibble'] = "flamble"
        expected_path = "/flibble/result_page"
        page = form.submit()
        assert page.path == expected_path

    def test_non_string_value(self):
        form = self.response.get_form()
        form['flibble'] = 1

    def test_missing_field(self):
        form = self.response.get_form()
        with nose.tools.assert_raises(KeyError) as e:
            form['_xyz_'] = "foo"
        assert "_xyz_" in str(e.exception)

    def test_set_select(self):
        form = self.response.get_form()
        form['select_field'] = "2"
        result = form.submit_data()
        assert result['select_field'] == "2"

    def test_set_radio(self):
        form = self.response.get_form()
        print(form.to_string())
        form['radio_field'] = "b"
        result = form.submit_data()
        assert result['radio_field'] == "b"

    def test_get_two_forms(self):
        response = Response(
            StubResponse(two_form_document), agent=self.agent)
        form_0 = response.get_form(index=0)
        assert form_0.action == "/result_page"
        form_1 = response.get_form(index=1)
        assert form_1.action == "/other_page"
