# -*- coding: utf-8 -*-

import mock

import testino as t


def test_xpath_func():
    with mock.patch.object(t, 'xpath_funcs', dict()):
        @t.xpath_func("//foo")
        def bar(element):
            return "flibble"

        assert t.xpath_funcs == dict(bar=[("//foo", bar)])


def test_element_wrapper_getattr():
    with mock.patch.object(t, 'xpath_funcs', dict()):
        @t.xpath_func("//foo")
        def bar(element):
            return "flibble"

        assert t._ElementWrapper("foobar").bar() == "flibble"


def test_element_wrapper_getattr_mulitple_funcs():
    with mock.patch.object(t, 'xpath_funcs', dict()):
        @t.xpath_func("//foo")
        def bar(element):
            return "foosome"
        first_bar = bar

        @t.xpath_func("//wang")
        def bar(element):
            return "wangle"
        second_bar = bar

        @t.xpath_func("//oob")
        def bar(element):
            return "oobles"
        third_bar = bar

        expected = dict(
            bar=[
                ("//foo", first_bar),
                ("//wang", second_bar),
                ("//oob", third_bar)])

        assert t.xpath_funcs == expected

        assert t._ElementWrapper("foogalicious").bar() == "foosome"
        assert t._ElementWrapper("foobar").bar() == "oobles"
        assert t._ElementWrapper("oobwangle").bar() == "oobles"
        assert t._ElementWrapper("ding wangle").bar() == "wangle"
