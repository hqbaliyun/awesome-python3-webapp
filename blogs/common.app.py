#!user/bin/env python3
# -*- coding: utf-8 -*-

""" web基类 """
import asyncio
import logging

from aiohttp import web
from aiohttp.web_runner import AppRunner

__author__ = 'hqb'

logging.basicConfig(level= logging.INFO)


def index(request):
    return web.Response(body='<h1>Awesome</h1>', headers={'content-type': 'text/html'})


app = web.Application()
app.router.add_get('/', index)
logging.info('Server start at http://127.0.0.1:9000')
web.run_app(app, host='127.0.0.1', port=9000)
