from . import index_blu


# 最开始的index
# @app.route('/index')
@index_blu.route("/index")  # 使用蓝图对象注册路由
def index():
    # current_app.logger.debug("哇哈哈，输出测试日志")
    return "index"
