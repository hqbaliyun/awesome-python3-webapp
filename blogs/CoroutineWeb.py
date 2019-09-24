#!usr/bin/env python3
# -*- coding: utf-8 -*-

"""
协程web
函数的五种类型: https://www.cnblogs.com/blackmatrix/p/6673220.html
"""
import asyncio
import functools
import inspect
import logging
import os
from urllib import parse

from aiohttp import web

from blogs.apis import APIError

__author__ = 'boris han'


def get(path):
    """
    自定义装饰器@get('/path')
    :param path: url路径
    :return:
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # 添加请求method=GET
        wrapper.__method__ = 'GET'
        # 添加请求URL
        wrapper.__route__ = path
        return wrapper

    return decorator


def post(path):
    """
    自定义装饰器@post
    :param path: 请求URL
    :return:
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # 添加请求method=POST
        wrapper.__method__ = 'POST'
        # 添加请求URL
        wrapper.__route__ = path
        return wrapper

    return decorator


def has_request_arg(fn):
    """
    判断是否有request参数
    :param fn:
    :return:
    """
    # 获取对象或函数的信息
    signature = inspect.signature(fn)
    # 当前函数参数列表
    parameters = signature.parameters
    found = False
    for name, param in parameters.items():
        if name == 'request':
            found = True
            continue

        # VAR_POSITIONAL - 可变参数 | KEYWORD_ONLY - 命名关键字参数 | VAR_KEYWORD - 关键字参数
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL
                      and param.kind != inspect.Parameter.KEYWORD_ONLY
                      and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function:%s%s'
                             % (fn.__name__, str(signature)))


def has_var_kwarg(fn):
    """
    判断指定函数是否包含关键字参数
    :param fn: 函数对象
    :return:
    """
    parameters = inspect.signature(fn).parameters
    for key, name in parameters.items():
        if name.kind == inspect.Parameter.VAR_KEYWORD:
            return True


def has_named_kwarg(fn):
    """
    判断指定函数是否包含命名关键字参数
    :param fn: 函数对象
    :return:
    """
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True


def get_named_kwarg(fn):
    """
    获得命名关键字参数
    :param fn:
    :return:
    """
    args = []
    parameters = inspect.signature(fn).parameters
    for name, param in parameters.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    # 返回一个不不可变的tuple
    return tuple(args)


def get_required_kwarg(fn):
    """
    获取必填的关键字参数(即没有默认值的关键字参数)
    :param fn: 函数对象
    :return:
    """
    args = []
    parameters = inspect.Signature(fn).parameters
    for name, param in parameters.items():
        # 关键字参数且默认值为空 = 必填关键字参数
        if param.kind == inspect.Parameter.VAR_KEYWORD and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)


class RequestHandler(object):

    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kwarg = has_var_kwarg(fn)
        self._has_named_kwarg = has_named_kwarg(fn)
        self._named_kwarg = get_named_kwarg(fn)
        self._required_kwarg = get_required_kwarg(fn)

    async def __call__(self, request):
        """
        RequestHandler回调函数
        :param request: 请求
        :return:
        """
        kw = None
        if self._has_var_kwarg or self._has_named_kwarg or self._required_kwarg:
            # POST请求
            if request.method == 'POST':
                if not request.content_type:
                    logging.error('Missing content type.')
                    return web.HTTPBadRequest()
                content_type = request.content_type.lower()
                if content_type.startwith('application/json'):
                    params = await request.json()
                    if not isinstance(params, dict):
                        logging.error('JSON body must be object.')
                        return web.HTTPBadRequest()
                    kw = params
                elif content_type.startwith('application/x-www-form-urlencoded') or \
                        content_type.startwith('multipart/form-data'):
                    params = await request.post()
                    kw = params
                else:
                    logging.error('Unsupported content type:%s.' % request.content_type)
                    return web.HTTPBadRequest()
            # GET请求
            if request.method == 'GET':
                query_params = request.query_string
                if query_params:
                    kw = dict()
                    for key, value in parse.parse_qs(query_params, True).items():
                        kw[key] = value[0]
        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kwarg and self._named_kwarg:
                # 移除所有的非命名关键字参数
                copy = dict()
                for name in self._named_kwarg:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy

            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args:%s' % k)
                kw[k] = v

        if self._has_request_arg:
            kw['request'] = request

        if self._required_kwarg:
            for name in self._required_kwarg:
                if name not in kw:
                    logging.error('Missing argument: %s.' % name)
                    return web.HTTPBadRequest()
        logging.info('call with args: %s ' % str(kw))
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)


def add_static(app):
    """
      添加静态资源路径
    :param app:
    :param func:
    :return:
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static: %s => %s.' % ('/static/', path))


def add_route(app, func):
    """
      注册模块URL
    :param app:
    :param func:
    :return:
    """
    method = getattr(func, '__method__', None)
    path = getattr(func, '__route__', None)
    if method is None or path is None:
        raise ValueError('@get or @post not defined in %s.' % str(func))
    if not asyncio.iscoroutinefunction(func) and not inspect.iscoroutinefunction(func):
        func = asyncio.coroutine(func)
    logging.info('add route %s %s => %s(%s)' %
                 (method, path, func.__name__, ','.join(inspect.signature(func).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, func))


def add_routes(app, module_name):
    """
    将所有module_name模块全部注册
    :param app:
    :param module_name:
    :return:
    """
    index = module_name.rfind('.')
    if index == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[index + 1]
        mod = getattr(__import__(module_name[:index], globals(), locals(), [name]), name)
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        func = getattr(mod, attr)
        if callable(func):
            method = getattr(func, '__method__', None)
            path = getattr(func, '__route__', None)
            if method and path:
                add_route(app, func)
