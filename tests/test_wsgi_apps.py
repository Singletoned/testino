# -*- coding: utf-8 -*-

import httpbin
import nose.tools

from testino import WSGIAgent, NotFound


def test_follow():
    agent = WSGIAgent(httpbin.app)
    response = agent.post("/redirect-to?url=/get")
    response = response.follow()
    assert response.status_code == 200
    assert response.path == "/get"


def test_404():
    agent = WSGIAgent(httpbin.app)
    with nose.tools.assert_raises(NotFound) as e:
        agent.get("/status/404")
    assert e.exception.response.status_code == 404
