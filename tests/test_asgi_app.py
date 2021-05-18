# -*- coding: utf-8 -*-

from testino import ASGIAgent


from fastapi import FastAPI

app = FastAPI()


@app.get("/users/{user_id}")
def read_user(user_id: str):
    return {'user_id': user_id}


def test_get():
    agent = ASGIAgent(app)
    response = agent.get("/users/foo")
    assert response.json() == {'user_id': "foo"}
