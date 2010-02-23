from flea import TestAgent
from nose.tools import assert_equal

from pesto import dispatcher_app, Response
from pesto.wsgiutils import with_request_args
dispatcher = dispatcher_app()
match = dispatcher.match

def page(html):
    def page(func):
        def page(request, *args, **kwargs):
            return Response(html % (func(request, *args, **kwargs)))
        return page
    return page

class testapp(object):

    @match('/redirect1', 'GET')
    def redirect1(request):
        return Response.redirect('/redirect2')

    @match('/redirect2', 'GET')
    def redirect2(request):
        return Response.redirect('/page1')

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
    def form_text(request):
        return {}

    @match('/form', 'GET')
    @page('''
          <html><body>
          <form method="POST" action="/postform">
            <input name="a" value="a" type="text" />
            <input name="a" value="" type="text" />
            <input name="b" value="" />
            <input name="c" value="1" type="checkbox" />
            <input name="c" value="2" type="checkbox" />
            <input name="r" value="1" type="radio" />
            <input name="r" value="2" type="radio" />
            <textarea name="t"></textarea>
            <input type="submit" name="s" value="s1"/>
            <input type="submit" name="s" value="s2"/>
            </form>
          </body></html>
    ''')
    def form(request):
        return {}

    @match('/postform', 'POST')
    def form_submit(request):
        return Response([
                '; '.join("%s:<%s>" % (name, value) for (name, value) in sorted(request.form.allitems()))
        ])

    @match('/getform', 'GET')
    def form_submit(request):
        return Response([
                '; '.join("%s:<%s>" % (name, value) for (name, value) in sorted(request.query.allitems()))
        ])

    @match('/setcookie', 'GET')
    @with_request_args(name=unicode, value=unicode, path=unicode)
    def setcookie(request, name='foo', value='bar', path='/'):
        return Response(['ok']).add_cookie(name, value, path=path)

    @match('/cookies', 'GET')
    @match('/<path:path>/cookies', 'GET')
    def listcookies(request, path=None):
        print request.environ
        return Response([
                '; '.join("%s:<%s>" % (name, value.value) for (name, value) in sorted(request.cookies.allitems()))
        ])


def test_click():
    page = TestAgent(dispatcher).get('/page1')
    assert_equal(
        page.click("//a[1]").request.path_info,
        '/page1'
    )
    assert_equal(
        page.click("//a[2]").request.path_info,
        '/page2'
    )

def test_get_with_query_is_correctly_handled():
    page = TestAgent(dispatcher).get('/getform?x=1')
    assert_equal(page.body, "x:<1>")

def test_click_follows_redirect():

    response = TestAgent(dispatcher).get('/page1')["//a[text()='redirect']"].click(follow=False)
    assert_equal(response.request.path_info, '/redirect1')

    response = TestAgent(dispatcher).get('/page1')["//a[text()='redirect']"].click(follow=True)
    assert_equal(response.request.path_info, '/page1')

def test_form_text():
    form_page = TestAgent(dispatcher).get('/form-text')
    form = form_page['//form']
    # Check defaults are submitted
    assert_equal(
        form.submit().body,
        "a:<>; a:<a>; b:<>"
    )

    # Now set field values
    form['//input[@name="a"][1]'].value = 'do'
    form['//input[@name="a"][2]'].value = 're'
    form['//input[@name="b"][1]'].value = 'mi'
    assert_equal(
        form.submit().body,
        "a:<do>; a:<re>; b:<mi>"
    )

def test_form_checkbox():
    form_page = TestAgent(dispatcher).get('/form-checkbox')
    form = form_page['//form']
    # Check defaults are submitted
    assert_equal(
        form.submit().body,
        "b:<A>"
    )

    # Now set field values
    form['//input[@name="a"][1]'].checked = True
    form['//input[@name="a"][2]'].checked = True
    form['//input[@name="b"][1]'].checked = False
    form['//input[@name="b"][2]'].checked = True
    assert_equal(
        form.submit().body,
        "a:<1>; a:<2>; b:<B>"
    )

def test_cookies_are_received():
    response = TestAgent(dispatcher).get('/setcookie?name=foo;value=bar;path=/')
    assert_equal(response.cookies['foo'].value, 'bar')
    assert_equal(response.cookies['foo']['path'], '/')

def test_cookies_are_resent():
    response = TestAgent(dispatcher).get('/setcookie?name=foo;value=bar;path=/')
    response = response.get('/cookies')
    assert_equal(response.body, 'foo:<bar>')

def test_cookie_paths_are_observed():
    response = TestAgent(dispatcher).get('/setcookie?name=doobedo;value=dowop;path=/')
    response = response.get('/setcookie?name=dowahdowah;value=beebeebo;path=/private')

    response = response.get('/cookies')
    assert_equal(response.body, 'doobedo:<dowop>')

    response = response.get('/private/cookies')
    assert_equal(response.body, 'doobedo:<dowop>; dowahdowah:<beebeebo>')



