import logging

import redis


class Config(object):
    """工程配置信息"""

    # 默认日志等级
    LOG_LEVEL = logging.DEBUG

    # 配置mysql数据库信息
    # 数据库链接
    SQLALCHEMY_DATABASE_URI = "mysql://root:mysql@127.0.0.1:3306/information2"  # 注意别写错了，不然会告警
    # SQLALCHEMY_BINDS = {}  # 不知道为甚这次不加这个会告警；原因是上面那条写错了
    # 动态追踪修改设置，如未设置只会提示警告
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    # 配置redis信息
    # redis地址
    REDIS_HOST = "127.0.0.1"
    # redis端口
    REDIS_PORT = 6379

    # session私钥
    SECRET_KEY = "EjpNVSNQTyGi1VvWECj9TvC/+kq3oujee2kTfQUs8yCM6xX9Yjq52v54g+HVoknA"
    SESSION_TYPE = "redis"  # 指定session保存到redis中
    SESSION_USE_SIGNER = True  # 让cookie中的session_id被加密签名处理
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT)  # 使用redis的实例
    PERMANENT_SESSION_LIFETIME = 86400  # session的有效期，单位是秒


class DevelopementConfig(Config):
    """开发模式"""
    # 开启debug模式
    DEBUG = True


class ProductionConfig(Config):
    """生产模式"""
    # 生产模式下的日志等级
    LOG_LEVEL = logging.ERROR


config = {
    "development": DevelopementConfig,
    "production": ProductionConfig
}