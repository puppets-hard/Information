# 公共函数
import functools

from flask import session, current_app, g

from info.models import User


# 公共函数，获取登陆的用户模型
def user_login_data(f):
    # 增加@functools.wraps(f), 可以保持当前装饰器去装饰的函数的 __name__ 的值不变
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get('user_id')
        user = None

        if user_id:
            try:
                user = User.query.get(user_id)  # 根据用户id查询数据库
            except Exception as e:
                current_app.logger.error(e)

        g.user = user  # 返回查询对象
        return f(*args, **kwargs)

    return wrapper


# 过滤器，需要在app中注册
def do_index_class(index):
    """自定义过滤器，过滤点击排行的序号class"""
    if index == 1:
        return "first"
    elif index == 2:
        return "second"
    elif index == 3:
        return "third"
    else:
        return ""
