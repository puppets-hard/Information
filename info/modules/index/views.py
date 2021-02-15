from flask import session, current_app, jsonify

from info.models import User
from info.utils.response_code import RET
from . import index_blu


# 最开始的index
# @app.route('/index')
@index_blu.route("/index")  # 使用蓝图对象注册路由
def index():
    # current_app.logger.debug("哇哈哈，输出测试日志")
    # 获取登陆中的用户信息
    user_id = session.get('user_id')
    data = None
    if user_id:
        try:
            user = User.query.get(user_id)
            data = user.to_dict() if user else None

        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.USERERR, errmsg='未知错误')
    return jsonify(data)

