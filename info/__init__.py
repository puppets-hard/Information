import logging
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
import redis

from config import config  # 这个注意下目录位置：info的init文件相当于和info目录统计

# db = SQLAlchemy(app)  # 创建数据库对象
db = SQLAlchemy()  # 这里从上面修改
# 创建一个redis实例
# redis_store = redis.StrictRedis(host=DevelopementConfig.REDIS_HOST, port=DevelopementConfig.REDIS_PORT)
redis_store = None  # 这里从上面修改为None值


def setup_log(config_name):
    """配置日志"""
    # 设置日志的记录等级
    logging.basicConfig(level=config[config_name].LOG_LEVEL)
    # 创建日志记录器， 指明日志保存的路径，每个日志文件的最大大小，保存的日志文件个数的数量上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024*1024*100, backupCount=10)
    # 创建日志的记录格式，日志等级，输入日志信息的文件名，行数，日志信息
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s]:{%(filename)s line:%(lineno)d} {message:%(message)s}')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)  # 接管日志信息


# 添加一个工厂方法，根据传入的配置不同创建其对应的应用实例
def create_app(config_name):
    # 设置项目日志
    setup_log(config_name)

    app = Flask(__name__)

    app.config.from_object(config[config_name])  # 从配置对象中加载配置

    db.init_app(app)  # 这里创建数据库对象，代替了db = SQLAlchemy(app)

    global redis_store
    # 创建一个redis实例
    redis_store = redis.StrictRedis(host=config[config_name].REDIS_HOST, port=config[config_name].REDIS_PORT)

    # csrf保护开启，CSRFProtect只做验证工作，cookie中的 csrf_token 和表单中的 csrf_token 需要我们自己实现
    # CSRFProtect(app)
    # 开启session
    Session(app)

    from info.modules.index import index_blu  # 导入写好的蓝图
    # 注册蓝图,当我们在应用对象上注册一个蓝图时，可以指定一个url_prefix关键字参数（这个参数默认是/）
    app.register_blueprint(index_blu)

    from info.modules.passport import passport_blu
    app.register_blueprint(passport_blu, url_prefix='/passport')

    from info.modules.news import news_blu
    app.register_blueprint(news_blu, url_prefix='/news')

    from info.modules.profile import profile_blu
    app.register_blueprint(profile_blu, url_prefix='/profile')

    return app
