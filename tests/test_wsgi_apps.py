# -*- coding: utf-8 -*-

import httpbin
import nose.tools

from testino import WSGIAgent, NotFound, MethodNotAllowed


def test_follow_get():
    agent = WSGIAgent(httpbin.app)
    response = agent.get("/redirect-to?url=/get")
    assert response.status_code == 302
    response = response.follow()
    assert response.status_code == 200
    assert response.path == "/get"


def test_follow_post():
    agent = WSGIAgent(httpbin.app)
    response = agent.post("/redirect-to?url=/get")
    assert response.status_code == 302
    response = response.follow()
    assert response.status_code == 200
    assert response.path == "/get"


def test_non_html():
    agent = WSGIAgent(httpbin.app)
    response = agent.get("/robots.txt")
    assert not response.lxml


def test_404():
    agent = WSGIAgent(httpbin.app)
    with nose.tools.assert_raises(NotFound) as e:
        agent.get("/status/404")
    assert e.exception.response.status_code == 404


def test_405():
    agent = WSGIAgent(httpbin.app)
    with nose.tools.assert_raises(MethodNotAllowed) as e:
        agent.post("/status/405")
    assert e.exception.response.status_code == 405
