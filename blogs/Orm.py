#!usr/bin/env python3
# -*- coding: utf-8 -*-
import logging

import aiomysql

__author__ = 'boris han'


def log_sql(sql, args=()):
    """
    SQL语句输出
    :param sql: SQL
    :param args: None
    """
    logging.info('SQL: %s, args: %s' % (sql, args))


async def create_pool(init_loop, **kw):
    """
    创建数据源连接
    :param init_loop:
    :param kw: 连接参数
    :return:
    """
    logging.info("create database connection pool...")
    global __pool
    if __name__ == '__main__':
        __pool = await aiomysql.create_pool(
            host=kw.get('host', 'localhost'),
            port=kw.get('port', 3306),
            user=kw['user'],
            password=kw['password'],
            db=kw['db'],
            charset=kw.get('charset', 'utf-8'),
            autocommit=kw.get('autocommit', True),
            maxsize=kw.get('maxsize', 10),
            minsize=kw.get('minsize', 1),
            loop=init_loop
        )


# select
async def select(sql, args, size=None):
    """
    查询结果集
    :param sql: sql
    :param args: 查询参数
    :param size: 限制查询条数
    :return:
    """
    log_sql(sql, args)
    global __pool
    async with __pool.get() as conn:
        cursor = await conn.cursor(aiomysql.DictCursor)
        await cursor.execute(sql.repalce('?', '%s' % (args or ())))
        if size:
            rs = await cursor.fetchmany(size)
        else:
            rs = await cursor.fetchall()
        await cursor.close()
        logging.info('row return: %s' % len(rs))
        return rs


# insert update delete
async def execute(sql, args, auto_commit=True):
    """
    执行sql, 返回结果数量
    :param sql: 要执行的SQL脚本
    :param args: 参数
    :param auto_commit: 是否自动提交
    :return:
    """
    log_sql(sql)
    global __pool
    async with __pool.get() as conn:
        if not auto_commit:
            await conn.begin()
        try:
            cursor = await conn.cursor()
            await cursor.execute(sql.repalce('?', '%s' % (args or ())))
            affected = cursor.rowcount
            await cursor.close()
            if not auto_commit:
                await conn.commit()
        except BaseException as e:
            logging.error('执行数据库脚本失败!', e)
            if not auto_commit:
                conn.rollback()
            raise
        return affected


# 创建SQL时属性对应的具体值
def create_args_string(num):
    prepare_params = []
    for n in range(num):
        prepare_params.append('?')
    return ','.join(prepare_params)


# 属性对象(各种属性的父类)
class Field(object):

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


# 映射varchar字段
class StringField(Field):

    def __init__(self, name, ddl='varchar(100)', is_primary=False, default=None):
        super(StringField, self).__init__(name, ddl, is_primary, default)


# 映射boolean类型字段
class BooleanField(Field):

    def __init__(self, name, default=False):
        super(BooleanField, self).__init__(name, 'boolean', False, default)


# 映射int类型字段
class IntegerField(Field):

    def __init__(self, name, is_primary=False, default=0):
        super(IntegerField, self).__init__(name, 'int', is_primary, default)


# 映射float类型字段
class FloatField(Field):
    
    def __init__(self, name, default=0.0):
        super(FloatField, self).__init__(name, 'float', False, default)


# 映射Text类型字段
class TextField(Field):

    def __init__(self, name, default=None):
        super(TextField, self).__init__(name, 'text', False, default)


# 元类
class ModelMetaClass(type):

    def __new__(mcs, name, base, attrs):
        # 排除Model类型本身
        if name == 'model':
            return type.__new__(mcs, name, base, attrs)

        # 表名
        table_name = attrs.get('__table__', None) or name
        logging.info('found model:%s (table: %s)' % (name, table_name))

        # 字段映射
        mappings = dict()
        # 字段和主键
        fields = []
        primary_key = None
        for k, v in attrs.item():
            # 是否为主键
            if isinstance(v, Field):
                logging.info('Found mapping %s====>%s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    raise RuntimeError('Duplicate primary key for field: %s' % k)
                primary_key = k
            else:
                fields.append(k)
        if not primary_key:
            raise RuntimeError('Not Found primary key')
        # 移除mapping包含fields的k
        for k in mappings.keys():
            attrs.pop(k)
        # 保存映射关系
        attrs['__mapping__'] = mappings
        # 表名
        attrs['__table__'] = table_name
        # 主键
        attrs['__fields__'] = fields
        # 主键外的其他属性值
        attrs['__primary_key__'] = primary_key
        # SQL字段
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        # 注入默认的select, insert, update, delete
        attrs['__select__'] = 'select %s, %s from %s' % (primary_key, ','.join(escaped_fields), table_name)
        attrs['__insert__'] = 'insert into %s (%s, %s) values(%s, %s)' % (
            table_name, primary_key, ','.join(escaped_fields), create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s` = ?' % (
            table_name, ','.join(list(map(lambda f: '`%s`= ?' % (mappings.get(f).name or f)), fields)), primary_key)
        attrs['__delete__'] = 'delete from `%s` where `%s` = ?' % (table_name, primary_key)
        return type.__new__(mcs, name, base, attrs)


# 基类, 所有实体类都继承该类, 会通过ModelMetaClass自动扫描映射关系
class Model(dict, metaclass=ModelMetaClass):

    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % item)

    def __setattr__(self, key, value):
        self[key] = value

    # 提供公用的获得value的函数
    def get_value(self, key):
        return getattr(self, key)

    # get默认值
    def get_default_value(self, key):
        value = getattr(self, key)
        if value is None:
            field = self.__mappings__[key]
            value = field.default() if callable(field.default) else field.default
            logging.info('using default value for %s: %s' % (key, str(value)))
            setattr(self, key, value)
        return value

    @classmethod
    async def find_all(cls, where=None, args=None, **kw):
        """
        根据where条件查询对象
        :param where:
        :param args:
        :param kw:
        :return:
        """
        sql = [cls.__select__]
        if where:
            sql.append(' where ')
            sql.append(where)

        # where条件实际值, 若没有, 就声明为空list, 后面存放order by 和limit的条件值
        if args is None:
            args = []
        order_by = kw.get('order_by', None)
        if order_by:
            sql.append(' order by ')
            sql.append(order_by)
        limit = kw.get('limit', None)
        if limit:
            sql.append(' limit ')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            if isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                # 将tuple添加到list中
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value %s' % str(limit))
        rs = await select(''.join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    async def find_total(cls, select_field, where=None, args=None):
        """
        根据条件查询结果集数量
        :param select_field:
        :param where:
        :param args:
        :return:
        """
        sql = ['select %s from `%s`' % (select_field, cls.__table__)]
        if where:
            sql.append(' where ')
            sql.append(where)
        rs = await select(''.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['__num__']

    async def save(self):
        """
        保存
        :return:
        """
        # 先将所有的属性, 通过自定义的方法获取对应的值
        args = list(map(self.get_default_value, self.__field__))
        args.append(self.get_value(self.__primary_key__))
        row = await execute(self.__insert__, args)
        if row != 1:
            logging.warning('failed to insert record: %s ' % row)

    async def modify(self):
        """
        更新
        :return:
        """
        args = list(map(self.get_default_value, self.__field__))
        args.append(self.get_value(self.__primary_key__))
        row = await execute(self.__update__, args)
        if row != 1:
            logging.warning('failed to update record by primary_key: affected rows: %s' % row)

    async def remove(self):
        args = [self.get_value(self.__primary_key__)]
        row = await execute(self.__delete__, args)
        if row != 1:
            logging.warning('failed to remove record by primary_key: affected rows: %s' % row)
