# !usr/bin/env python3
# -*- coding: utf-8 -*-

"""
  获取配置
"""
import logging

from blogs import config_default, config_override

__author__ = 'boris han'


class Dict(dict):
    """
      自定义字典类
    """
    def __init__(self, names=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v


    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(r"'Dict' has no attribute '%s'" % item)


    def __setattr__(self, key, value):
        self[key] = value


def merge(defaults, override):
    """
      合并两个配置文件的配置
    :param defaults:
    :param override:
    :return:
    """
    result = {}
    for k, v in defaults.items():
        if k in override:
            if isinstance(v, dict):
                result[k] = merge(v, override[k])
            else:
                result[k] = override[k]
        else:
            result[k] = v
    return result


def to_dict(target):
    """
      字典数据转换
    :param target:
    :return:
    """
    defined_dict = Dict()
    for k, v in target.items():
        defined_dict[k] = to_dict(v) if isinstance(v, dict) else v
    return defined_dict


configs = config_default.configs

try:
    configs = merge(configs, config_override.configs)
except ImportError as e:
    logging.error('导入配置文件异常', e)
