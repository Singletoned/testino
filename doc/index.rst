Flea
=====

Flea helps you test WSGI applications.

Contents:

.. toctree::
        :maxdepth: 2


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. include:: ../README

Driving WSGI applications
-------------------------

Use the ``TestAgent`` class to produce a user agent capable of driving your
WSGI application::

	>>> from flea import TestAgent
	>>> agent = TestAgent(my_wsgi_app)

You can now use this to navigate your WSGI application by...


.. testsetup:: *

        from pesto.request import Request
        from pesto.response import Response
        from pesto.testing import make_environ
        from pesto.wsgiutils import mount_app
        from flea import TestAgent
        agent = TestAgent(
                mount_app({
                        '/': Response(["""
                                                <a id="mylink" href="/">foo</a>
                                                <form name="login-form" action="/"></form>
                                                <form name="contact" action="/"><button type="submit" name="send"/></form>
                                                <form name="register" action="/register"></form>
                        """]),
                        '/register': Response.redirect('/', Request(make_environ()))
                })
        ).get('/')

Making GET requests:

.. doctest::

	>>> agent = agent.get('/my-page')

Making POST requests:

.. doctest::

	>>> agent = agent.post('/contact', data={'message': 'your father smells of elderberries'})

Clicking links:

.. doctest::

	>>> # Click on first <a> tag on page
	>>> agent = agent["//a[1]"].click()


	>>> # Click on first <a> tag with content 'foo'
	>>> agent = agent["//a[.='foo']"].click()

	>>> # Click on tag with id 'mylink'
	>>> agent = agent["//a[@id='mylink']"].click()

Submitting forms:

.. doctest::

	>>> agent = agent["//form"].submit()
	>>> agent = agent["//form[@name='login-form']"].submit()
	>>> agent = agent["//form[@name='contact']//button[@name='send']"].submit()

 Following HTTP redirects:
 
 	>>> agent = agent["//form[@name='register']"].submit()
 	>>> agent = agent.follow()
 
 	>>> # Or more succinctly...
 	>>> agent = agent["//form"].submit(follow=True)
 
Don't like XPath? Use CSS selectors instead::

	>>> agent = agent.findcss("a").click()
	>>> agent = agent.findcss("a.highlighted").click()
	>>> agent = agent.findcss("a#mylink").click()


Querying WSGI application responses
-----------------------------------

Checking the content of the request
`````````````````````````````````````

::

	>>> assert agent.request.path_info == '/index.html'
	>>> print agent.request.environ
        {...}

``agent.request`` is a `pesto.request.Request <http://pypi.python.org/pypi/pesto>`_
object, and all attributes of that class are available to examine.

Checking the content of the response
`````````````````````````````````````

::

	>>> assert agent.response.content_type == 'text/html'
	>>> assert agent.response.status == '200 OK'

Note that ``agent.response`` is a `pesto.testing.TestResponse
<http://pypi.python.org/pypi/pesto>`_ object, and all attributes of that class
are available.


Checking returned content.
``````````````````````````````

The ``.body`` property contains the raw response
from the server::
	
	>>> assert 'you are logged in' in agent.body

Any element selected via an xpath query has various helper methods useful for
inspecting the document.

Checking if strings are present in an HTML element
``````````````````````````````````````````````````

::

	>>> assert 'Welcome back' in agent['//h1']

Accessing the html of selected elements
```````````````````````````````````````

::

	>>> agent['//p[1]'].html()
	<p>Eat, drink and be <strong>merry!</strong></p>

NB this is the html parsed and reconstructed by lxml, so is unlikely to be the literal HTML emitted by your application - use ``agent.body`` for that.

Accessing textual content of selected elements
````````````````````````````````````````````````
::

	>>> agent['//p[1]'].striptags()
	Eat, drink and be merry!


Flea API documention
--------------------

.. automodule:: flea
        :members:



