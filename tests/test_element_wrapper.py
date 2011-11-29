# -*- coding: utf-8 -*-

import testino as t

def test_xpath_func():
    @t.xpath_func("foo")
    def bar(element):
        return "flibble"

    assert t.xpath_funcs == dict(bar=[("foo", bar)])

def test_element_wrapper_getattr():
    @t.xpath_func("foo")
    def bar(element):
        return "flibble"

    assert t._ElementWrapper("foobar").bar() == "flibble"

