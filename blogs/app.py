#!usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    异步框架
"""
import json
import logging
import os
import time
import asyncio

from aiohttp import web
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from blogs import Orm
from blogs.CoroutineWeb import add_routes, add_static

__author__ = 'boris han'


def init_jinja2(app, **kw):
    logging.info('init jinja2...')
    options=dict(
        autoescape=kw.get('autoescape', True),
        block_start_string = kw.get('block_start_string', '{%'),
        block_end_string = kw.get('block_end_string', '%}'),
        variable_start_string=kw.get('variable_start_string', '{{'),
        variable_end_string=kw.get('variable_end_string', '}}'),
        auto_reload=kw.get('auto_reload', True)
    )
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: %s.' % path)
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env


async def logger_factory(app, handler):

    logging.info("app=%s" % str(app))

    async def logger(request):
        logging.info('Request:%s %s' % (request.method, request.path))
        return await handler(request)

    return logger


async def data_factory(app, handler):
    logging.info('start data_factory in app: %s' % app)
    async def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = await request.json()
                logging.info('request json: %s.' % str(request.__data__))
            elif request.content_type.startswith('application/x-wwww-form-urlencoded'):
                request.__data__= await request.post()
                logging.info('request form: %s.' % str(request.__data__))
        return await handler(request)
    return parse_data


async def response_factory(app, handler):
    """
      响应统一处理
    :param app:
    :param handler:
    :return:
    """

    async def response(request):
        logging.info('Response handler...')
        r = await handler(request)

        # 字符串直接返回
        if isinstance(r, web.StreamResponse):
            return r
        # 字节流按照流的方式返回
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        # 转发请求, 直接转发到指定页面
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html; charset=utf-8'
            return resp
        # JSON请求按照json返回
        if isinstance(r, dict):
            template = r.get('__template__')
            # 没模板直接返回数据
            if template is None:
                resp = web.Response(body=json.dumps(r, ensure_ascii=False,
                                                    default=lambda msg: msg.__dict__).encode('utf-8'))
                resp.content_type = 'application/json; charset=utf-8'
                return resp
            # 有模板将数据放入模板, 返回页面
            else:
                resp = web.Response(body=app['__template__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html; charset=utf-8'
                return resp
        # int类型直接返回
        if isinstance(r, int) and 100 < r < 600:
            return web.Response(r)
        # tuple直接返回
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and 100 < t < 600:
                return web.Response(t, str(m))
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain; charset=utf-8'
        return resp
    return response


def datetime_filter(special_time):
    """
      格式化时间
    :param special_time: 指定格式化的时间
    """
    time_diff = int(time.time() - special_time)
    if time_diff < 60:
        return u'1分钟前.'
    if time_diff < 3600:
        return u'%s分钟前.' % (time_diff // 60)
    if time_diff < 86400:
        return u'%s小时前.' % (time_diff // 3600)
    if time_diff < 604800:
        return u'%s天前.' % (time_diff // 86400)
    format_datetime = datetime.fromtimestamp(time_diff)
    return u'%s年%s月%s日' % (format_datetime.year, format_datetime.month, format_datetime.day)


async def init(loop):
    await Orm.create_pool(
        init_loop=loop, host='127.0.0.1', user='test', password='Aas_12345678', db='awesome')
    app = web.Application(loop=loop, middlewares=[logger_factory, response_factory])
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    add_routes(app, 'handlers')
    add_static(app)
    await web.run_app(app, host='127.0.0.1', port=9000)


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
