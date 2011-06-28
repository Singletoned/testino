# -*- coding: utf-8 -*-

import collections
import functools
from StringIO import StringIO

from nose.tools import assert_equal, assert_raises

import werkzeug as wz
from werkzeug import html

from lxml.html import tostring

import testino
from testino import TestAgent

tostring = functools.partial(tostring, encoding="utf-8")

def page(html):
    def page(func):
        def page(request, *args, **kwargs):
            return wz.Response(html % (func(request, *args, **kwargs)))
        return page
    return page


class FormApp(object):
    """
    A WSGI application that responds to GET requests with the given
    HTML, and POST requests with a dump of the posted info
    """


    def __init__(self, formhtml, action=None, enctype="application/x-www-form-urlencoded"):

        if action is None:
            action = "/"

        self.formhtml = formhtml
        self.action = action
        self.enctype = enctype

    def __call__(self, environ, start_response):
        return getattr(self, environ['REQUEST_METHOD'])(environ, start_response)

    def GET(self, environ, start_response):
        return wz.Response(
            [
                '<html><body><form method="POST" action="%s" enctype="%s">%s</form></body></html>' % (
                    self.action,
                    self.enctype,
                    self.formhtml,
                )
            ]
        )(environ, start_response)

    def POST(self, environ, start_response):
        items = sorted(wz.Request(environ).form.items(multi=True))
        return wz.Response([
                '; '.join(
                    "%s:<%s>" % (name, value)
                    for (name, value) in items
                )
        ])(environ, start_response)

def dispatch(url_map, environ, start_response):
    request = wz.Request(environ)
    request.url_map = url_map.bind_to_environ(environ)
    try:
        endpoint, kwargs = request.url_map.match()
        response = endpoint(request, **kwargs)
    except wz.exceptions.HTTPException, e:
        response = e
    return response(environ, start_response)

def GET(path=None):
    return (u"GET", func)

def POST(path=None):
    return (u"POST", func)

class MockAppMeta(type):
    def __new__(meta, cls_name, bases, cls_dict):
        cls = type.__new__(meta, cls_name, bases, cls_dict)
        cls.url_map = wz.routing.Map()
        for key, value in cls_dict.items():
            if not key.startswith("__"):
                cls.url_map.add(
                    wz.routing.Rule("/"+key, methods=[value[0]], endpoint=value[1]))
        return cls

class MockApp(object):
    __metaclass__ = MockAppMeta
    def __new__(cls, environ, start_response):
        return dispatch(cls.url_map, environ, start_response)

url_map = wz.routing.Map()

def match(rule, method):
    def decorate(f):
        r = wz.routing.Rule(rule, methods=[method], endpoint=f)
        url_map.add(r)
        return f
    return decorate

class TestApp(object):
    def __call__(self, environ, start_response):
        return dispatch(url_map, environ, start_response)

    @match('/redirect1', 'GET')
    def redirect1(request):
        return wz.redirect('/redirect2')

    @match('/redirect2', 'GET')
    def redirect2(request):
        return wz.redirect('/page1')

    @match('/page1', 'GET')
    @page('''
          <html><body>
          <a href="page1">page 1</a>
          <a href="page2">page 2</a>
          <a href="redirect1">redirect</a>
          </body></html>
    ''')
    def page1(request):
        return {}

    @match('/page2', 'GET')
    @page('''<html><html>''')
    def page2(request):
        return {}

    @match('/form-text', 'GET')
    @page('''
          <html><body>
          <form method="POST" action="/postform">
            <input name="a" value="a" type="text" />
            <input name="a" value="" type="text" />
            <input name="b" value="" type="text" />
          </form>
          </body></html>
    ''')
    def form_text(request):
        return {}

    @match('/bad-link', 'GET')
    @page('''
        <html><body>
        <a href="page_that_does_not_exist">A Bad Link</a>
        </body></html>
    ''')
    def bad_link(request):
        return {}

    @match('/form-checkbox', 'GET')
    @page('''
          <html><body>
          <form method="POST" action="/postform">
            <input name="a" value="1" type="checkbox" />
            <input name="a" value="2" type="checkbox" />
            <input name="b" value="A" type="checkbox" checked="checked" />
            <input name="b" value="B" type="checkbox" />
          </form>
          </body></html>
    ''')
    def form_checkbox(request):
        return {}

    @match('/form-mixed', 'GET')
    def form_mixed(request):
        return wz.Response('''
        <html><body>
        <form method="POST" action="/postform">
          <fieldset>
            <select name="s">
              <option value="O1" selected="selected">Option 1</option>
              <option value="O2">Option 2</option>
            </select>
          </fieldset>
          <input name="a" value="A" type="text">
          <input name="b" value="B" type="text">
        </form>
        </body></html>
        ''')

    @match('/postform', 'POST')
    def form_submit(request):
        return wz.Response([
                '; '.join("%s:<%s>" % (name, value) for (name, value) in sorted(request.form.items(multi=True)))
        ])

    @match('/getform', 'GET')
    def form_submit(request):
        return wz.Response([
                '; '.join("%s:<%s>" % (name, value) for (name, value) in sorted(request.args.items(multi=True)))
        ])

    @match('/setcookie', 'GET')
    def setcookie(request, name='', value='', path=''):
        name = name or request.args['name']
        value = value or request.args['value']
        path = path or request.args.get('path', None) or '/'
        response = wz.Response(['ok'])
        response.set_cookie(name, value, path=path)
        return response

    @match('/cookies', 'GET')
    @match('/<path:path>/cookies', 'GET')
    def listcookies(request, path=None):
        return wz.Response([
                '; '.join("%s:<%s>" % (name, value) for (name, value) in sorted(request.cookies.items()))
        ])

def test_all():
    page = TestAgent(TestApp()).get('/form-checkbox')
    for name in ['a', 'b']:
        elements = page.all("//input[@name=$name]", name=name)
        for element in elements:
            assert element.element.attrib['name'] == name

    page = TestAgent(TestApp()).get('/form-checkbox')
    form = page.form
    data = [
        dict(name="a", type="checkbox"),
        dict(name="b", type="checkbox")]
    for datum in data:
        xpath = "input[@name=$name and @type=$type]"
        elements = form.all(xpath, **datum)
        for element in elements:
            for key, value in datum.items():
                assert element.element.attrib[key] == value

def test_one():
    page = TestAgent(TestApp()).get('/page1')
    assert_raises(
        testino.MultipleMatchesError,
        page.one,
        "//a"
    )
    assert_raises(
        testino.NoMatchesError,
        page.one,
        "//h1"
    )

    for href in ['page1', 'page2']:
        element = page.one("//a[@href=$href]", href=href)
        assert element.element.attrib['href'] == href

    page = TestAgent(TestApp()).get('/form-mixed')
    form = page.form
    data = [
        dict(name="a", value="A", type="text"),
        dict(name="b", value="B", type="text")]
    for datum in data:
        xpath = "input[@name=$name and @value=$value and @type=$type]"
        element = form.one(xpath, **datum)
        for key, value in datum.items():
            assert element.element.attrib[key] == value

def test_reset():
    agent = TestAgent(TestApp())
    assert_raises(
        testino.NoRequestMadeError,
        agent.reset
    )
    page = agent.get(u'/form-text')
    assert page.one(u"//input[@name='a'][1]").value == u'a'
    page.one(u"//input[@name='a'][1]").value = u'foobar'
    assert page.one(u"//input[@name='a'][1]").value == u'foobar'
    page.reset()
    assert page.one(u"//input[@name='a'][1]").value == u'a'
    input_b = page.one(u"//input[@name='b']")
    assert input_b.value == u''
    input_b.value = u'flibble'
    assert input_b.value == u'flibble'
    page.reset()
    assert input_b.value == u''

def test_click():
    page = TestAgent(TestApp()).get('/page1')
    assert_equal(
        page.one("//a[1]").click().request.path,
        '/page1'
    )
    assert_equal(
        page.one("//a[2]").click().request.path,
        '/page2'
    )
    assert_equal(
        len(page.all("//a")),
        3
    )
    assert_raises(
        testino.MultipleMatchesError,
        page.one,
        "//a"
    )
    assert_equal(
        page.click('//a[1]').request.path,
        page.one('//a[1]').click().request.path
    )
    assert_equal(
        page.click(text=u'page 1').request.path,
        page.one('//a[text()="page 1"]').click().request.path
    )
    assert_equal(
        page.click(href=u'page1').request.path,
        page.one('//a[@href="page1"]').click().request.path
    )
    assert_equal(
        page.click(text=u'page 1', href=u'page1').request.path,
        page.one('//a[text()="page 1" and @href="page1"]').click().request.path
    )

def test_rows_to_dict():
    body_1 = """
<table>
  <thead>
    <tr>
      <th>foo</th> <th>bar</th> <th>baz</th>
    </tr>
  </thead>
  <tr>
    <td>
      1
    </td>
    <td>
      2
    </td>
    <td>
      3
    </td>
  </tr>
  <tr>
    <td>4</td> <td>5</td> <td>6</td>
  </tr>
</table>
    """
    body_2 = """
<table>
  <thead>
    <tr>
      <th><a href="">foo</a></th> <th>bar</th> <th>baz</th>
    </tr>
  </thead>
  <tr>
    <td>1</td> <td>2</td> <td>3</td>
  </tr>
  <tr>
    <td>4</td> <td>5</td> <td>6</td>
  </tr>
</table>
    """
    for body in [body_1, body_2]:
        agent = TestAgent(wz.Response(body)).get('/')
        row = agent.one(u'//tr[td][1]')
        assert row.headers() == ["foo", "bar", "baz"]
        expected = dict(foo='1', bar='2', baz='3')
        for key in expected:
            assert_equal(expected[key], row.to_dict()[key])

def test_tables():
    header_values = ["foo", "bar", "baz"]
    table_text = html.table(
        html.thead(
            html.tr(
                *[html.th(html.span(i+" ")) for i in header_values])),
        html.tr(
            *[html.td(i) for i in [1, 2, 3]]),
        html.tr(
            *[html.td(i) for i in [4, 5, 6]]))
    agent = TestAgent(wz.Response([table_text])).get(u'/')
    table = agent.one(u"//table")
    rows = [row.to_dict() for row in table.rows()]
    headers = table.headers()
    assert len(headers) == 3
    assert headers == header_values
    assert len(rows) == 2
    for i, row in enumerate(rows):
        for j, header in enumerate(header_values):
            index = (i * 3) + (j + 1)
            assert row[header] == str(index)
            assert row[header] == type(row[header])(index)
        for j, cell in enumerate(row.values()):
            index = (i * 3) + (j + 1)
            assert cell == str(index)
    lists = [
        ['1', '2', '3'],
        [4, 5, 6],
    ]
    for row, l in zip(table.rows(), lists):
        row.assert_is(l)
    assert_raises(
        AssertionError,
        table.rows()[0].assert_is,
        ['flim', 'flam', 'flooble']
        )

def test_empty_rows():
    body = """
<table>
  <tr>
    <td></td><td></td><td></td>
  </tr>
</table>
    """
    agent = TestAgent(wz.Response(body)).get(u'/')
    row = agent.one(u'//tr')
    row.assert_is([None, '', u''])

def test_unicode_chars():
    body_text = html.div(
        html.p(u"£")).encode('utf-8')
    agent = TestAgent(wz.Response([body_text]))
    page = agent.get(u'/')
    assert page.body == body_text
    assert tostring(page.lxml) == body_text
    assert page.html().encode('utf-8') == body_text
    div_element = page.one('//div')
    assert div_element.html().encode('utf-8') == body_text
    assert tostring(div_element.lxml) == body_text

def test_html_returns_unicode():
    body_text = html.div(
        html.p(u"£")).encode('utf-8')
    agent = TestAgent(wz.Response([body_text]))
    page = agent.get(u'/')
    assert page.html() == body_text.decode('utf-8')
    assert page.html('utf-8') == body_text

def test_lxml_attr_is_consistent():
    body_text = html.div(
        html.p(u"foo")).encode('utf-8')
    agent = TestAgent(wz.Response([body_text]))
    page = agent.get(u'/')
    div_element = page.one('//div')
    assert page.lxml == div_element.lxml

def test_lxml_attr_doesnt_reset_forms():
    form_page = TestAgent(TestApp()).get('/form-text')
    form = form_page.one('//form')
    # Set field values
    form.one('//input[@name="a"][1]').value = 'do'
    form.one('//input[@name="a"][2]').value = 're'
    form.one('//input[@name="b"][1]').value = 'mi'
    # Check page body
    assert "form" in tostring(form_page.lxml)
    # Check form values
    assert form.one('//input[@name="a"][1]').value == 'do'
    assert form.one('//input[@name="a"][2]').value == 're'
    assert form.one('//input[@name="b"][1]').value == 'mi'

def test_click_ignores_fragment():
    class UrlFragmentApp(MockApp):
        page1 = (u"GET", lambda r: wz.Response(['<a href="/page2#fragment">link to page 1</a>']))
        page2 = (u"GET", lambda r: wz.Response(['This is page2']))
    agent = TestAgent(UrlFragmentApp)
    assert_equal(
        agent.get('/page1').one("//a").click().request.path,
        '/page2')

def test_css_selectors_are_equivalent_to_xpath():
    page = TestAgent(TestApp()).get('/page1')
    assert_equal(
        list(page.all('//a')),
        list(page.all('a', css=True))
    )

def test_get_with_query_is_correctly_handled():
    page = TestAgent(TestApp()).get('/getform?x=1')
    assert_equal(page.body, "x:<1>")

def test_click_follows_redirect():
    page = TestAgent(TestApp()).get('/page1')
    link = page.one("//a[text()='redirect']")
    response = link.click(follow=False)
    assert_equal(response.request.path, '/redirect1')

    page = TestAgent(TestApp()).get('/page1')
    link = page.one("//a[text()='redirect']")
    response = link.click(follow=True)
    assert_equal(response.request.path, '/page1')

def test_post_404():
    page = TestAgent(TestApp()).post('/no_page_here', status="404 NOT FOUND")
    assert page.status == "404 NOT FOUND"

def test_click_404_raises_error():
    page = TestAgent(TestApp()).get('/bad-link')
    link = page.one("//a[text()='A Bad Link']")
    assert_raises(
        testino.PageNotFound,
        link.click
    )

def test_bad_response():
    assert_raises(
        testino.BadResponse,
        TestAgent(TestApp()).get,
        '/',
        status="666 A Bad Status",
    )

def test_form_field_container():
    form_page = TestAgent(TestApp()).get('/form-mixed')
    form = form_page.one('//form')
    assert form.fields[u's'] == "O1"

def test_form_text():
    form_page = TestAgent(TestApp()).get('/form-text')
    form = form_page.one('//form')
    # Check defaults are submitted
    assert_equal(
        form.submit().body,
        "a:<>; a:<a>; b:<>"
    )

    # Now set field values
    form.one('//input[@name="a"][1]').value = 'do'
    form.one('//input[@name="a"][2]').value = 're'
    form.one('//input[@name="b"][1]').value = 'mi'
    assert_equal(
        form.submit().body,
        "a:<do>; a:<re>; b:<mi>"
    )

def test_select_default_option():
    body = """
    <form method="" id="" action="">
      <select name="words">
        <option value="floozle">Floozle</option>
        <option value="flamble">Flamble</option>
        <option value="blat">Blat</option>
        <option value="blop">Blop</option>
      </select>
    </form>
    """
    page = TestAgent(wz.Response(body)).get(u'/')
    form = page.form
    assert form['words'] == "floozle"
    assert form.one("//option[@value=$value]", value="floozle").selected

def test_form_checkbox():
    form_page = TestAgent(TestApp()).get('/form-checkbox')
    form = form_page.one('//form')
    # Check defaults are submitted
    assert_equal(
        form.submit().body,
        "b:<A>"
    )

    # Now set field values
    form.one('//input[@name="a"][1]').checked = True
    form.one('//input[@name="a"][2]').checked = True
    form.one('//input[@name="b"][1]').checked = False
    form.one('//input[@name="b"][2]').checked = True
    assert form.one('//input[@name="a"][1]').checked == True
    assert form.one('//input[@name="a"][2]').checked == True
    assert form.one('//input[@name="b"][1]').checked == False
    assert form.one('//input[@name="b"][2]').checked == True
    
    assert_equal(
        form.submit().body,
        "a:<1>; a:<2>; b:<B>"
    )

def test_form_getitem():
    form_text = html.div(
        html.p(
            html.input(type="text", name="foo", value="flam")),
        html.p(
            html.select(
                html.option(value="a", selected=True),
                html.option(value="b"),
                name="bar"))
    )
    form_page = TestAgent(FormApp(form_text)).get(u'/')
    form = form_page.one(u'//form')
    assert form['foo'] == "flam"
    assert form['bar'] == "a"
    form["foo"] = u"flibble"
    form["bar"] = u"a"
    assert form.one(u'//input').value == u'flibble'
    assert form.one(u'//select').value == u'a'

    # Test checkboxes
    form_page = TestAgent(TestApp()).get('/form-checkbox')
    form = form_page.one('//form')
    assert form['a'] == []
    assert form['b'] == ["A"]

def test_form_getitem_doesnt_match():
    form_text = html.body(
        html.form(
            html.input(name="foo", value="a")),
        html.input(name="foo", value="b"))
    agent = TestAgent(wz.Response([form_text]))
    form_page = agent.get(u'/')
    form = form_page.one(u"//form")
    assert form[u"foo"] == u"a"

def test_form_setitem():
    form_page = TestAgent(TestApp()).get('/form-checkbox')
    form = form_page.one('//form')
    assert_raises(
        AssertionError,
        form.__setitem__,
        'a',
        ['1', '2', '3'])

def test_form_checkbox_value_property():
    form = TestAgent(FormApp("""
        <input name="a" value="1" type="checkbox"/>
        <input name="a" value="2" type="checkbox"/>
    """)).get('/').form

    form.one('//input[@name="a"][1]').checked = True
    form.one('//input[@name="a"][2]').checked = True
    assert form.one('//input[@name="a"][1]').value == '1'
    assert form.one('//input[@name="a"][2]').value == '2'
    assert form['a'] == ['1', '2']

    form.one('//input[@name="a"][1]').checked = False
    form.one('//input[@name="a"][2]').checked = True
    assert form.one('//input[@name="a"][1]').value == None
    assert form.one('//input[@name="a"][2]').value == '2'
    assert form['a'] == ['2']

    form.one('//input[@name="a"][1]').checked = False
    form.one('//input[@name="a"][2]').checked = False
    assert form.one('//input[@name="a"][1]').value == None
    assert form.one('//input[@name="a"][2]').value == None
    assert form['a'] == []

    form.one('//input[@name="a"][1]').value = ['1', '2']
    assert form.one('//input[@name="a"][1]').checked == True
    assert form.one('//input[@name="a"][2]').checked == True
    assert form['a'] == ['1', '2']

    form.one('//input[@name="a"][1]').value = ['1']
    assert form.one('//input[@name="a"][1]').checked == True
    assert form.one('//input[@name="a"][2]').checked == False
    assert form['a'] == ['1']

    form.one('//input[@name="a"][1]').value = []
    assert form.one('//input[@name="a"][1]').checked == False
    assert form.one('//input[@name="a"][2]').checked == False
    assert form['a'] == []


def test_form_radio_value_property():
    form = TestAgent(FormApp("""
        <input name="a" value="1" type="radio"/>
        <input name="a" value="2" type="radio"/>
    """)).get('/').form

    assert form['a'] == None
    form.one('//input[@name="a"][2]').checked = True
    assert form['a'] == '2'
    assert form.one('//input[@name="a"][1]').value == '2'
    assert form.one('//input[@name="a"][2]').value == '2'

    form['a'] = '1'
    assert form.one('//input[@name="a"][1]').checked == True
    assert form.one('//input[@name="a"][2]').checked == False
    assert form.one('//input[@name="a"][1]').value == '1'
    assert form.one('//input[@name="a"][2]').value == '1'

    form['a'] = '2'
    assert form.one('//input[@name="a"][1]').checked == False
    assert form.one('//input[@name="a"][2]').checked == True

    form['a'] = None
    assert form.one('//input[@name="a"][1]').checked == False
    assert form.one('//input[@name="a"][2]').checked == False

def test_form_textarea():
    form_page = TestAgent(FormApp('<textarea name="t"></textarea>')).get('/')
    # Test empty submission
    form = form_page.form
    data = form.submit_data()
    assert data == [("t", "")]
    el = form_page.one('//textarea')
    assert el.submit_value == ""
    # Test non empty submission
    el.value = 'test'
    assert_equal(
        form_page.one('//textarea').form.submit().body,
        't:<test>'
    )
    assert el.submit_value == 'test'
    form = form_page.form
    form['t'] = "Mr Flibble says hello!"
    assert form.submit_data() == [("t", "Mr Flibble says hello!")]

def test_form_select():
    app = FormApp("""
        <select name="s">
        <option value="o1"></option>
        <option value="o2"></option>
        </select>
    """)
    r = TestAgent(app).get('/')
    assert_equal(r.form.submit().body, 's:<o1>')

    r.one('//select').value = 'o2'
    assert r.one('//select/option[2]').selected
    assert_equal(r.form.submit().body, 's:<o2>')

    r = TestAgent(app).get('/')
    r.one('//select/option[2]').selected = True
    r.one('//select/option[1]').selected = True
    assert_equal(r.form.submit().body, 's:<o1>')

def test_form_select_select():
    app = FormApp("""
        <select name="s">
        <option value="o1">O1: Text with '</option>
        <option value="o2">O2: Text with \"</option>
        </select>
    """)
    r = TestAgent(app).get('/')
    r.one('//select').select('O1: Text with \'')
    assert r.one('//select/option[1]').selected == True
    assert_equal(r.one('//form').submit().body, 's:<o1>')

    r = TestAgent(app).get('/')
    r.one('//select').select(u'O1: Text with \'')
    r.one('//select').select(u'O2: Text with \"')
    assert r.one('//select/option[1]').selected == False
    assert r.one('//select/option[2]').selected == True
    assert_equal(r.one('//form').submit().body, 's:<o2>')

    app = FormApp("""
        <select name="s">
        <option value="o1">Same text</option>
        <option value="o2">Same text</option>
        </select>
    """)
    r = TestAgent(app).get('/')
    assert_raises(
        testino.MultipleMatchesError,
        r.one('//select').select,
        'Same text')

def test_form_select_multiple():
    app = FormApp("""
        <select name="s" multiple="">
        <option value="o1"></option>
        <option value="o2"></option>
        <option value="o3"></option>
        </select>
    """)
    r = TestAgent(app).get('/')
    r.one('//select').value = ['o1', 'o3']
    assert_equal(r.one('//form').submit().body, 's:<o1>; s:<o3>')

    r = TestAgent(app).get('/')
    r.one('//select/option[3]').selected = True
    r.one('//select/option[2]').selected = True
    assert_equal(r.one('//form').submit().body, 's:<o2>; s:<o3>')

def test_form_radio():
    app = FormApp("""
        <input name="a" value="1" type="radio"/>
        <input name="a" value="2" type="radio"/>
        <input name="b" value="3" type="radio"/>
        <input name="b" value="4" type="radio"/>
    """)
    r = TestAgent(app).get('/')
    r.all('//*[@name="a"]')[0].checked = True
    r.all('//*[@name="b"]')[0].checked = True
    assert_equal(r.one('//form').submit().body, 'a:<1>; b:<3>')

    r = TestAgent(app).get('/')
    r.one('//*[@name="a"][1]').checked = True
    r.one('//*[@name="a"][2]').checked = True
    assert_equal(r.one('//form').submit().body, 'a:<2>')

def test_form_hidden():
    form_page = TestAgent(FormApp('<input name="t" value="1" type="hidden"/>')).get('/')
    assert_equal(
        form_page.one('//form').form.submit().body,
        't:<1>'
    )


def test_form_disabled():
    form_page = TestAgent(FormApp('<input name="t" value="1" type="text" disabled="" />')).get('/')
    assert_equal(
        form_page.one('//form').form.submit().body,
        ''
    )


def test_form_input_no_type():
    form_page = TestAgent(FormApp('<input name="t" value="1" />')).get('/')
    assert_equal(form_page.one('//form').form.submit().body, 't:<1>')

def test_form_file_input_value_requires_3tuple():
    r = TestAgent(FormApp('<input name="upload" type="file" />')).get('/')
    try:
        r.one('//input').value = 'photo.jpg'
    except ValueError:
        pass
    else:
        raise AssertionError("Expecting a ValueError")

    r = TestAgent(FormApp('<input name="upload" type="file" />')).get('/')
    try:
        r.one('//input').value = ('photo.jpg', '123123')
    except ValueError:
        pass
    else:
        raise AssertionError("Expecting a ValueError")

    r.one('//input').value = ('photo.jpg', 'text/jpeg', '123123')

def test_form_file_input_requires_stores_values():
    r = TestAgent(FormApp('<input name="upload" type="file" />')).get('/')
    r.one('//input').value = ('photo.jpg', 'text/jpeg', '123123')
    assert_equal(r.one('//input').value, ('photo.jpg', 'text/jpeg', '123123'))

def test_form_file_input_submits_file_data():

    class TestApp(FormApp):
        def POST(self, environ, start_response):
            req = wz.Request(environ)
            fu = req.files['upload']
            assert isinstance(fu, wz.FileStorage)
            assert fu.read() == '123123'
            return wz.Response(['ok'])(environ, start_response)

    r = TestAgent(TestApp('<input name="upload" type="file" />', enctype="multipart/form-data")).get('/')
    r.one('//input').value = ('photo.jpg', 'text/jpeg', '123123')
    r.one('//form').submit()

    r = TestAgent(TestApp('<input name="upload" type="file" />', enctype="multipart/form-data")).get('/')
    r.one('//input').value = ('photo.jpg', 'text/jpeg', StringIO('123123'))
    r.one('//form').submit()


def test_form_submit_button():
    app = FormApp('''
        <input id="1" type="submit" name="s" value="1"/>
        <input id="2" type="submit" name="s" value="2"/>
        <input id="3" type="submit" name="t" value="3"/>
        <input id="4" type="image" name="u" value="4"/>
        <button id="5" type="submit" name="v" value="5">click me!</button>
        <button id="6" name="w" value="6">click me!</button>
        <button id="7" type="button" name="x" value="7">don't click me!</button>
    ''')
    form_page = TestAgent(app).get('/')

    assert_equal(form_page.one('//form').submit().body, '')
    assert_equal(form_page.one('//form').submit_data(), [])

    assert_equal(form_page.one('#1', css=True).submit().body, 's:<1>')
    assert_equal(form_page.one('#1', css=True).submit_data(), [('s', '1')])
    assert_equal(form_page.one('#2', css=True).submit().body, 's:<2>')
    assert_equal(form_page.one('#2', css=True).submit_data(), [('s', '2')])
    assert_equal(form_page.one('#3', css=True).submit().body, 't:<3>')
    assert_equal(form_page.one('#3', css=True).submit_data(), [('t', '3')])
    assert_equal(form_page.one('#4', css=True).submit().body, 'u.x:<1>; u.y:<1>')
    assert form_page.one('#4', css=True).submit_data() == [('u.x', '1'), ('u.y', '1')]
    assert_equal(form_page.one('#5', css=True).submit().body, 'v:<5>')
    assert_equal(form_page.one('#5', css=True).submit_data(), [('v', '5')])
    assert_equal(form_page.one('#6', css=True).submit().body, 'w:<6>')
    assert_equal(form_page.one('#6', css=True).submit_data(), [('w', '6')])
    try:
        form_page.one('#7', css=True).submit()
    except NotImplementedError:
        pass
    else:
        raise AssertionError("Shouldn't be able to submit a non-submit button")

    try:
        form_page.one('#7', css=True).submit_data()
    except NotImplementedError:
        pass
    else:
        raise AssertionError("Shouldn't be able to call submit_data on a non-submit button")

def test_form_data_set():
    html_form = '''
    <html><body>
      <form method="POST" id="flibble" action="/flibble">
        <input type="text" name="foo" value="">
        <input type="text" name="bar" value="">
        <input type="text" name="baz" value="" disabled>
        <input type="text" value="flibble">
        <select name="wordchoice">
          <option value="blamble">Blamble!</option>
          <option value="bloozle">Bloozle!!</option>
          <option value="plop">Plop!!!</option>
        </select>
        <select name="colours" multiple>
          <option value="puce">Puce</option>
          <option value="maroon">Maroon</option>
          <option value="beige">Beige</option>
          <option value="eggshell">eggshell</option>
        </select>
        <input type="submit" name="submit" value="Draft">
        <input type="submit" name="submit" value="Draft">
        <input type="reset" name="reset" value="Reset">
        <input type="reset" name="reset" value="Reset">
        <input type="submit" name="submit" value="Save">
        <input type="submit" name="submit" value="Save">
        <input type="submit" value="Save">
        <button name="empty" value="empty">
      </form>
    </body></html>'''
    page = TestAgent(wz.Response(html_form)).get('/')
    form = page.form
    baz = form.one("input[@name='baz']")
    form['foo'] = "foo_value"
    form['bar'] = "bar_value"
    form['colours'] = ['puce', 'beige']
    draft_button = form.one('input[@value="Draft"][1]')
    data = form.data_set(button=draft_button)
    assert data == [
        ('foo', "foo_value"),
        ('bar', "bar_value"),
        ('wordchoice', "blamble"),
        ('colours', 'puce'),
        ('colours', 'beige'),
        ('submit', "Draft")]
    assert data == draft_button.submit_data()
    data = form.data_set()
    assert data == [
        ('foo', "foo_value"),
        ('bar', "bar_value"),
        ('wordchoice', "blamble"),
        ('colours', 'puce'),
        ('colours', 'beige')]

def test_form_submit_selects_a_default_button():
    html_form = '''
    <html><body>
      <form method="POST" id="flibble" action="/flibble">
        <input type="text" name="foo" value="">
        <input type="submit" name="submit" value="Save">
      </form>
    </body></html>'''
    page = TestAgent(wz.Response(html_form)).get('/')
    form = page.form
    assert form.submit_data() == [("foo", ""), ("submit", "Save")]

def test_form_action_fully_qualified_uri_doesnt_error():
    app = FormApp("", action='http://localhost/')
    r = TestAgent(app).get('/')
    assert_equal(r.one('//form').submit().body, '')

def test_form_submit_follows_redirect():
    form_page = TestAgent(TestApp()).get('/form-text')
    form_page.one('//form').attrib['method'] = 'get'
    form_page.one('//form').attrib['action'] = '/redirect1'
    assert_equal(
        form_page.one('//form').submit(follow=True).request.path,
        '/page1'
    )

def test_form_attribute_returns_parent_form():
    form_page = TestAgent(TestApp()).get('/form-text')
    assert_equal(form_page.all('//input[@name="a"]')[0].form, form_page.one('//form'))

def test_cookies_are_received():
    response = TestAgent(TestApp()).get('/setcookie?name=foo&value=bar&path=/')
    assert_equal(response.cookies['foo'].value, 'bar')
    assert_equal(response.cookies['foo']['path'], '/')

def test_cookies_are_resent():
    response = TestAgent(TestApp()).get('/setcookie?name=foo&value=bar&path=/')
    response = response.get('/cookies')
    assert_equal(response.body, 'foo:<bar>')

def test_cookie_paths_are_observed():
    response = TestAgent(TestApp()).get('/setcookie?name=doobedo&value=dowop&path=/')
    response = response.get('/setcookie?name=dowahdowah&value=beebeebo&path=/private')

    response = response.get('/cookies')
    assert_equal(response.body, 'doobedo:<dowop>')

    response = response.get('/private/cookies')
    assert_equal(response.body, 'doobedo:<dowop>; dowahdowah:<beebeebo>')

def test_back_method_returns_agent_to_previous_state():
    saved = agent = TestAgent(TestApp()).get('/page1')
    agent = agent.one("//a[.='page 2']").click()
    assert agent.request.path == '/page2'
    agent = agent.back()
    assert agent.request.path == '/page1'
    assert agent is saved

def test_back_method_skips_redirects():
    saved = agent = TestAgent(TestApp()).get('/page2')
    agent = agent.get('/redirect1', follow=True)
    assert agent.request.path == '/page1'
    agent = agent.back()
    assert agent.request.path == '/page2'
    assert agent is saved

def test_context_manager_allows_checkpointing_history():
    saved = agent = TestAgent(TestApp()).get('/page1')

    with agent as a2:
        a2 = a2.one("//a[.='page 2']").click()
        assert a2.request.path == '/page2'

    assert agent.request.path == '/page1'
    assert agent is saved

def test_html_method_returns_string_representation():
    agent = TestAgent(wz.Response(['<p>I would like an ice lolly</p>'])).get('/')
    assert_equal(
        agent.root_element.html(),
        '<p>I would like an ice lolly</p>'
    )

def test_striptags_method_returns_string_representation():
    agent = TestAgent(wz.Response(['<p>And a nice <strong>cup of tea</strong>!</p>'])).get('/')
    assert_equal(
        agent.root_element.striptags(),
        'And a nice cup of tea!'
    )

def test_striptags_on_string():
    assert_equal(
        testino.striptags('<p>Hullo<p>'),
        'Hullo'
        )

def test_striptags_keep_breaks():
    body = """
    <p>10 Downing Street<br>
    Westminster <br>
    London </p>
    """
    expected = """10 Downing Street\nWestminster\nLondon"""
    agent = TestAgent(wz.Response(body)).get('/')
    assert_equal(
        expected,
        agent.root_element.striptags(convert_breaks=True)
        )

def test_striptags_handles_nesting():
    body = """
    <tr>
        <td>line 1</td>
        <td>line 2</td>
    </tr>
    """
    agent = TestAgent(wz.Response([body])).get('/')
    assert_equal(
        agent.root_element.striptags(),
        "line 1 line 2"
    )

def test_striptags_handles_trailing_newline():
    agent = TestAgent(wz.Response(['<tr><td>flimmel</td>\n</tr>'])).get('/')
    assert_equal(
        agent.one('//td').striptags(),
        'flimmel'
    )

def test_in_operator_works_on_elementwrapper():
    agent = TestAgent(wz.Response(['<p>Tea tray tea tray tea tray tea tray</p>'])).get('/')
    assert 'tea tray' in agent.one('//p')
    assert 'tea tray' in agent.all('//p')[0]
    assert 'teat ray' not in agent.one('//p')
    assert 'teat ray' not in agent.all('//p')[0]

def test_regexes_enabled_in_xpath():
    agent = TestAgent(wz.Response(['<html><p>salt</p><p>pepper</p><p>pickle</p>'])).get('/')
    assert [tag.text for tag in agent._find("//*[re:test(text(), '^p')]")] == ['pepper', 'pickle']
    assert [tag.text for tag in agent._find("//*[re:test(text(), '.*l')]")] == ['salt', 'pickle']

def test_get_allows_relative_uri():
    agent = TestAgent(wz.Response(['<html><p>salt</p><p>pepper</p><p>pickle</p>']))
    try:
        agent.get('../')
    except AssertionError:
        # Expect an AssertionError, as we haven't made an initial request to be
        # relative to
        pass
    else:
        raise AssertionError("Didn't expect relative GET request to work")
    agent = agent.get('/rhubarb/custard/')
    agent = agent.get('../')
    assert_equal(agent.request.url, 'http://localhost/rhubarb/')

def test_form_fill_with_single_values():
    form_page = TestAgent(FormApp('''
            <input name="p" type="text"/>
            <textarea name="q"/>
            <input name="r" type="text"/>
    ''')).get('/')
    form_page.form.fill(
        p = 'plum',
        q = 'quince',
        r = 'raspberry',
    )
    assert_equal(
        form_page.form.submit_data(),
        [('p', 'plum'), ('q', 'quince'), ('r', 'raspberry')]
    )

def test_form_fill_with_xpath_expressions():
    form_page = TestAgent(FormApp('''
            <input name="p" type="text"/>
            <textarea name="q" type="text"/>
            <input name="r" type="text"/>
    ''')).get('/')
    form_page.form.fill(
        ('input[1]', 'plum'),
        ('textarea', 'quince'),
        ('input[2]', 'raspberry'),
    )
    assert_equal(
        form_page.form.submit_data(),
        [('p', 'plum'), ('q', 'quince'), ('r', 'raspberry')]
    )

def test_form_fill_with_multiple_values():
    form_page = TestAgent(FormApp('''
            <input name="p" type="text"/>
            <input name="q" type="text" value='Q' />
            <input name="p" type="text"/>
            <input name="r" type="text" value='R' />
            <input name="p" type="text"/>
    ''')).get('/')
    form_page.form.fill(
        p = ['a', 'b', 'c']
    )
    assert_equal(
        form_page.form.submit_data(),
        [('p', 'a'), ('q', 'Q'), ('p', 'b'), ('r', 'R'), ('p', 'c')]
    )
