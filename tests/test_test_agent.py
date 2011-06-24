# -*- coding: utf-8 -*-

import werkzeug as wz

import testino

def test_process_html5():
    body = """
    <html>
    <form method="" id="" action="">
      <input type="text" name="foo"/>
      <select name="words">
        <option value="floozle">Floozle</option>
        <option value="flamble">Flamble</option>
        <option value="blat">Blat</option>
        <option value="blop">Blop</option>
      </select>
    </form>
    </html>
    """
    agent = testino.TestAgent(wz.Response(body)).get()
    print agent.pretty()
    print dir(agent.form.element)
    # assert False

