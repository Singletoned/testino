# -*- coding: utf-8 -*-

import lxml

import mock

import testino as t


def test_xpath_func():
    with mock.patch.object(t, 'xpath_funcs', dict()):
        @t.xpath_func("foo")
        def bar(element):
            return "flibble"

        assert t.xpath_funcs == dict(bar=[("foo", bar)])


def test_element_wrapper_getattr():
    with mock.patch.object(t, 'xpath_funcs', dict()):
        @t.xpath_func("../form")
        def bar(element):
            return "flibble"

        element = lxml.html.fromstring("""<form></form>""")
        assert t._ElementWrapper(element).bar() == "flibble"


def test_element_wrapper_getattr_mulitple_funcs():
    with mock.patch.object(t, 'xpath_funcs', dict()):
        @t.xpath_func("../form")
        def bar(element):
            return "This is a form"
        first_bar = bar

        @t.xpath_func("../form[@method='POST']")
        def bar(element):
            return "This is a POST form"
        second_bar = bar

        @t.xpath_func("../form[@method='GET']")
        def bar(element):
            return "This is a GET form"
        third_bar = bar

        expected = dict(
            bar=[
                ("../form", first_bar),
                ("../form[@method='POST']", second_bar),
                ("../form[@method='GET']", third_bar)])

        assert t.xpath_funcs == expected

        form_element = lxml.html.fromstring(
            '''<form></form>''')
        form_GET_element = lxml.html.fromstring(
            '''<form method="GET"></form>''')
        form_POST_element = lxml.html.fromstring(
            '''<form method="POST"></form>''')
        form_DELETE_element = lxml.html.fromstring(
            '''<form method="DELETE"></form>''')
        div_element = lxml.html.fromstring('''<div><form method="DELETE"></form></div>''')


        assert t._ElementWrapper(form_element).bar() == "This is a form"
        assert t._ElementWrapper(form_POST_element).bar() == "This is a POST form"
        assert t._ElementWrapper(form_GET_element).bar() == "This is a GET form"
        assert t._ElementWrapper(form_DELETE_element).bar() == "This is a form"

        assert not t._ElementWrapper(div_element).bar
