#!usr/env/bin python3
# -*- coding: utf-8 -*-

""" web app用到的3个实体 """
import time
import uuid

from blogs.Orm import Model, StringField, BooleanField, FloatField, TextField

__author__ = 'boris han'


def next_id():
    """
    生成下一个主键id
    :return:
    """
    return '%0015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)


class Customer(Model):
    """
    用户
    """
    __table__ = 'customers'

    # 主键
    id = StringField(is_primary=True, default=next_id(), ddl='varchar(50)')
    # 邮件地址
    email = StringField(ddl='varchar(50)')
    # 登录密码
    password = StringField(ddl='varchar(50)')
    # 是否管理员
    admin = BooleanField()
    # 客户姓名
    name = StringField(ddl='varchar(50)')
    # 头像
    image = StringField(ddl='varchar(500)')
    # 创建时间
    created_at = FloatField(default=time.time)


class Blog(Model):
    """
    博客
    """
    __table__ = 'blog'

    # 主键
    id = StringField(is_primary=True, default=next_id(), ddl='varchar(50)')
    # 客户id
    customer_id = StringField(ddl='varchar(50)')
    # 客户名称
    customer_name = StringField(ddl='varchar(50)')
    # 客户头像
    customer_image = StringField(ddl='varchar(500)')
    # 博客名称
    name = StringField(ddl='varchar(50)')
    # 摘要
    summary = StringField(ddl='varchar(300)')
    # 内容
    content = TextField()
    # 创建时间
    created_at = FloatField(default=time.time)


class Comment(Model):
    """
    评论
    """
    __table__ = 'comment'

    # 主键
    id = StringField(is_primary=True, default=next_id(), ddl='varchar(50)')
    # 博客id
    blog_id = StringField(ddl='varchar(50)')
    # 客户id
    customer_id = StringField(ddl='varchar(50)')
    # 客户名称
    customer_name = StringField(ddl='varchar(50)')
    # 客户头像
    customer_image = StringField(ddl='varchar(500)')
    # 内容
    content = TextField()
    # 创建时间
    created_at = FloatField(default=time.time)
