#!usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    异步框架
"""
import json
import logging

from aiohttp import web

__author__ = 'boris han'


async def logger_factory(app, handler):

    logging.info("app=%s" % str(app))

    async def logger(request):
        logging.info('Request:%s %s' % (request.method, request.path))
        return await handler(request)

    return logger


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
