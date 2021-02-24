from flask import session, current_app, jsonify, g, render_template

from info.models import User, News, Category
from info.common import user_login_data
from info.utils.response_code import RET
from info import constants
from . import index_blu


# 最开始的index
# @app.route('/index')
@index_blu.route("/index")  # 使用蓝图对象注册路由
@user_login_data
def index():
    # current_app.logger.debug("哇哈哈，输出测试日志")
    # 获取登陆中的用户信息
    # user_id = session.get('user_id')
    # user = None  # 先定义变量，避免try失败后无数据导致出错

    # 用户登陆信息
    # if user_id:  # 如果user_id不存在会在查询的时候告警
    #     try:
    #         user = User.query.get(user_id)  # 返回主键对应的行，不存在则返回None
    #     except Exception as e:
    #         current_app.logger.error(e)

    # 新闻点击排行榜
    news_list = None  # 新闻列表查询变量声明
    try:
        # 查询点击排行反向排序，限制10个（order_by:根据指定条件对原查询结果进行排序，返回一个新查询)
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
    click_news_dict_list = []  # 点击排行榜信息列表声明
    for news in news_list if news_list else []:  # 从查询对象中取出每条新闻的信息字典
        click_news_dict_list.append(news.to_basic_dict())  # 将字典放入一个列表中

    # 新闻分类展示
    categories = None  # 新闻分类列表查询变量声明
    try:
        categories = Category.query.all()  # 查询所有的新闻分类
    except Exception as e:
        current_app.logger.error(e)
    category_dict_list = []  # 新闻分类信息列表声明
    for category in categories if categories else []:  # 从查询对象中取出每条新闻分类的信息字典
        category_dict_list.append(category.to_dict())  # 将字典放入一个列表中

    data = {  # 用字典装需要返回的数据
        # 用g变量和装饰器提取相同的查询登陆的用户信息操作
        'user_info': g.user.to_dict() if g.user else None,  # 格式化用户信息
        'click_news_list': click_news_dict_list,
        'categories': category_dict_list
    }

    # return jsonify(data)  # 返回json数据
    return render_template('news/index.html', data=data)  # 可以根据Flask创建app的important_name找到new


# 网站图标展示
@index_blu.route('/favicon.ico')
def favicon():
    return current_app.send_static_file('news/favicon.ico')  # 这个根据static找
