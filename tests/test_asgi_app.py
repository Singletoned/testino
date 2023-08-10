# -*- coding: utf-8 -*-

from fastapi import FastAPI

from testino import ASGIAgent

app = FastAPI()


@app.get("/users/{user_id}")
def read_user(user_id: str):
    return {"user_id": user_id}


def test_get():
    agent = ASGIAgent(app)
    response = agent.get("/users/foo")
    assert response.json() == {"user_id": "foo"}
