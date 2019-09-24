#!usr/bin/env python3
#-*- coding: utf-8 -*-

"""
  url 请求控制器
"""
from blogs.CoroutineWeb import get
from blogs.entity import Customer

__author__ = 'boris han'


@get('/')
async def index(request):
    user = await Customer.find_all()
    return {
        '__template': 'test.html',
        'users': user
    }
