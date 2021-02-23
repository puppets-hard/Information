import time

from flask import jsonify, g, request, current_app, session

from info import db, constants
from info.models import News
from info.utils.response_code import RET
from info.common import user_login_data
from . import profile_blu


# 用户资料展示
@profile_blu.route('/user_info', methods=['GET'])
@user_login_data
def user_info():
    # 获取登陆用户模型
    user = g.user

    # 校验是否登陆
    if not user:
        return jsonify(errno=RET.OK, errmsg='用户未登录')

    # 返回数据
    data = {
        'user_info': user.to_dict()  # 从数据库中查找到用户信息
    }
    return jsonify(errno=RET.OK, errmsg='OK', data=data)


# 基本资料设置
@profile_blu.route('/set_base_info', methods=['GET', 'POST'])
@user_login_data
def set_base_info():
    # 获取登陆信息
    user = g.user

    # 校验是否登陆
    if not user:
        return jsonify(errno=RET.OK, errmsg='用户未登录')

    # 如果是get方法， 返回用户的基本信息
    if request.method == 'GET':
        return jsonify(errno=RET.OK, errmsg='OK', data=user.to_dict())

    # 获取参数：nick_name, signature, gender
    data_json = request.json
    nick_name = data_json.get('nick_name')
    signature = data_json.get('signature')
    gender = data_json.get('gender')

    # 校验参数是否齐全
    if not all([nick_name, signature, gender]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')

    # 校验参数是否正确
    if gender not in(['MAN', 'WOMAN']):
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

    # 更新数据
    user.signature = signature
    user.nick_name = nick_name
    user.gender = gender
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, msg='信息保存失败')

    # 更新会话信息
    session['nick_name'] = nick_name

    # 返回成功
    return jsonify(errno=RET.OK, errmsg='OK')


# 用户头像
@profile_blu.route('/pic_info', methods=['POST'])
@user_login_data
def pic_info():
    # 获取用户登陆对象
    user = g.user

    # 校验用户是否登陆
    if not user:
        return jsonify(errno=RET.USERERR, errmsg='用户未登录')

    # 获取头像图片
    try:
        avatar_file = request.files.get('avatar')
        avatar_file = avatar_file.read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='读取头像错误')

    # 时间戳
    timestamp = int(time.time()) * 1000
    avatar_url = './avatar_pic/avatar_' + str(timestamp) + '.jpg'
    try:
        # 保存图片
        with open(avatar_url, 'wb') as f:
            f.write(avatar_file)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='保存图片失败')

    # 存地址到数据库
    user.avatar_url = avatar_url
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='数据库保存失败')

    # 返回数据
    return jsonify(errno=RET.OK, errmsg='OK', data={"avatar_url": avatar_url})


# 密码修改
@profile_blu.route('/password_info', methods=['POST'])
@user_login_data
def password_info():
    # 获取用户对象
    user = g.user

    # 判断用户是否登陆
    if not user:
        return jsonify(errno=RET.USERERR, errmsg='用户未登录')

    # 接收参数
    data_json = request.json
    old_password = data_json.get('old_password')
    new_password = data_json.get('new_password')

    # 校验参数是否齐全
    if not all([old_password, new_password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    # 校验旧密码
    if not user.check_password(old_password):
        return jsonify(errno=RET.PWDERR, errmsg="密码错误")

    # 修改密码
    user.password = new_password
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(3)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据库保存失败")

    # 返回成功
    return jsonify(errno=RET.OK, errmsg='OK')


# 收藏列表
@profile_blu.route('/collection', methods=['GET'])
@user_login_data
def user_collection():
    # 获取登陆的用户对象
    user = g.user

    # 判断是否登陆
    if not user:
        return jsonify(errno=RET.USERERR, errmsg='用户未登录')

    # 从查询字符串中获取参数,默认第一页
    page = request.args.get('p', 1)

    # 校验参数,如果参数不正确，默认为1
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    collections = []
    current_page = 1
    total_pages = 1
    try:
        # 查询数据库并分页
        # 参数是第几页， 每页多少条数据
        paginate = user.collection_news.paginate(page, constants.USER_COLLECTION_MAX_NEWS, False)
        # paginate对象中的新闻数据
        collections = paginate.items
        # 当前页
        current_page = paginate.page
        # 总页数
        total_pages = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    # 返回数据，默认第一页数据
    # 收藏dict的列表
    collection_dict_li = []
    for collection in collections:
        collection_dict_li.append(collection.to_basic_dict())

    data = {
        "total_pages": total_pages,
        "current_page": current_page,
        "collections": collection_dict_li
    }

    # 反回数据
    return jsonify(errno=RET.OK, errmsg="OK", data=data)


# 发布新闻
@profile_blu.route('/news_release', methods=['POST'])
@user_login_data
def news_release():
    # 获取用户的登陆对象
    user = g.user

    # 校验用户是否登陆
    if not user:
        return jsonify(errno=RET.USERERR, errmsg="用户未登陆")

    source = '个人发布'
    # 获取提交的数据
    data_form =request.form
    title = data_form.get('title')
    digest = data_form.get('digest')
    content = data_form.get('content')
    category_id = data_form.get('category_id')
    index_image = request.files.get('index_image')

    # 校验数据
    if not all([source, title, digest, content, category_id, index_image]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    # 尝试获取图片
    try:
        index_image = index_image.read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='读取图片出错')

    # 时间戳
    timestamp = int(time.time())*1000
    # 保存图片到本地
    pic_url = './pictures/image_'+str(timestamp)+'.jpg'
    try:
        with open(pic_url, 'wb') as f:
            f.write(index_image)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='保存图片失败')

    # 保存数据到数据库
    news = News()
    news.user_id = g.user.id
    news.title = title
    news.digest = digest
    news.source = source
    news.content = content
    news.index_image_url = pic_url
    news.category_id = category_id
    news.status = 1  # 1代表待审核状态

    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='保存数据失败')

    # 返回结果
    return jsonify(errno=RET.OK, errmsg='OK')


# 用户发表的新闻列表
@profile_blu.route('/news_list', methods=['GET'])
@user_login_data
def news_list():
    # 获取用户登陆对象
    user = g.user

    # 判断用户是否登陆
    if not user:
        return jsonify(errno=RET.USERERR, errmsg="用户未登录")

    # 从查询字符串中获取参数
    page = request.args.get('p', 1)

    # 校验参数是否正确，默认参数为1
    try:
        page = int(page)
    except Exception as e:
        current_app(e)
        page = 1

    news_li = []
    current_page = 1
    total_pages = 1
    try:
        # 查询数据库
        paginate = News.query.filter(News.user_id == user.id).paginate(page, constants.USER_COLLECTION_MAX_NEWS, False)
        # 获取当前页数据
        news_li = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_pages = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_li = []
    for news_item in news_li:
        news_dict_li.append(news_item.to_review_dict())
    data = {
        "news_list": news_dict_li,
        "total_page": total_pages,
        "current_page": current_page
    }
    # 返回数据
    return jsonify(data=data)