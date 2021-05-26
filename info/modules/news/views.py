from flask import request, jsonify, current_app, session, abort, g, render_template

from info import constants, db
from info.common import user_login_data
from info.models import News, User, Comment, CommentLike
from info.utils.response_code import RET
from . import news_blu


# 分局分类获取列表
@news_blu.route('/news_list', methods=['GET'])
def category_news_list():
    # 获取参数
    # data_json = request.json  # 不是json格式，而是查询字符串
    data_dict = request.args
    # print(data_dict)  # 打印ImmutableMultiDict([('cid', '1'), ('page', '1'), ('per_page', '50')])
    category_id = data_dict.get('cid', '1')  # 分类id
    page = data_dict.get('page', '1')  # 要获取的页数
    per_page = data_dict.get('per_page', constants.HOME_PAGE_MAX_NEWS)  # 每页的数据量，默认10条

    # 校验参数是否完整cid，page，per_page
    if not all([category_id, page, per_page]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')

    # 校验参数是否正确
    try:
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

    # 根据cid查询数据库，根据创建日期排序
    filters = []
    if category_id != '1':  # 如果不是1（默认所有最新新闻）
        filters.append(News.category_id == category_id)  # 将查询条件放入查询列表中
    try:
        # 在列表前加 * 号，会将列表拆分成一个一个的独立元素，不光是列表、元组、字典，由numpy生成的向量也可以拆分
        # 这里*filters相当于传了多个过滤条件进去             根据创建时间倒序            分页查询，返回分页对象
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, per_page, False)
        items = paginate.items  # 当前页的数据列表
        total_page = paginate.pages  # 总页数
        current_page = paginate.page  # 当前页码
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库查询错误')

    news_list = []
    for item in items:
        news_list.append(item.to_dict())  # 字典化查询到的数据信息，放入列表中

    # 返回数据
    return jsonify(errno=RET.OK, errmsg='OK', total_page=total_page, current_page=current_page, news_dict_li=news_list)


# 新闻详情页
@news_blu.route('/<int:news_id>', methods=['GET'])  # 用get方法在url中直接取得参数
@user_login_data  # 公共函数装饰器，放在info.common.py
def news_detail(news_id):
    # # 获取当前用户信息
    # user_id = session['user_id']
    # user = User.query.get(user_id)

    # 点击排行榜
    news_clicks_desc = None
    try:
        news_clicks_desc = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
    news_clicks_dict_list = []
    for news_click_desc in news_clicks_desc:
        news_clicks_dict_list.append(news_click_desc.to_basic_dict())

    # 新闻详情
    news = None
    try:
        # 根据新闻id查询新闻详情数据
        news = News.query.get(news_id)  # 根据news_id查询数据库
    except Exception as e:
        current_app.logger.error(e)
        abort(404)  # 返回404错误
    if not news:
        abort(404)

    try:
        news.clicks += 1  # 点击数量+1
        db.session.commit()  # 提交到数据库
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)

    # 收藏状态
    # 判断用户是否收藏, 默认为False
    is_collected = False
    # 判断用户是否收藏过该新闻
    if g.user:
        if news in g.user.collection_news:  # 如果新闻详情对象在登陆用户的收藏对象列表中
            is_collected = True  # 设置收藏标记

    # 评论列表
    comments = []
    try:
        # 根据新闻id查询所有评论，并按照创建时间倒序
        comments = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)

    # 该条新闻的所有评论id
    comment_ids = [comment.id for comment in comments]

    comment_likes_ids = []
    # 必须要登陆了才有点赞的评论
    if g.user:
        # 这个用户对现在这条新闻的 点赞评论列表        根据登陆的用户id，这条新闻的评论id查询
        comment_likes = CommentLike.query.filter(CommentLike.user_id == g.user.id, CommentLike.comment_id.in_(comment_ids)).all()
        # 提取登陆用户点赞了的评论id
        comment_likes_ids = [comment_like.comment_id for comment_like in comment_likes]

    comment_list = []
    for comment in comments:  # 遍历这条新闻的所有评论对象
        comment_dict = comment.to_dict()  # 评论对象信息字典化
        if g.user and (comment.id in comment_likes_ids):  # 如果用户登陆，该条品论id在点赞品论id中
            comment_dict['is_like'] = True  # 设置点赞标记True
        else:
            comment_dict['is_like'] = False  # 设置点赞标记False
        comment_list.append(comment_dict)

    # 返回数据
    data = {
        "user_info": g.user.to_dict() if g.user else None,  # 一登录的用户信息
        "click_news_list": news_clicks_dict_list,  # 点击排行展示
        "news": news.to_dict(),  # 新闻详情数据字典化
        "is_collected": is_collected,  # 该条新闻是否收藏
        "comments": comment_list  # 新闻评论
    }
    # return jsonify(errno=RET.OK, errmsg='OK', data=data)
    return render_template('news/detail.html', data=data)


# 新闻收藏
@news_blu.route('/news_collect', methods=['POST'])
@user_login_data
def news_collect():
    # 判断用户是否登陆
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg='用户未登陆')

    # 获取参数：news_id,action
    data_json = request.json
    news_id = data_json.get('news_id')
    action = data_json.get('action')

    # 校验参数是否齐全：news_id,action
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    if action not in ('collect', 'cancel_collect'):
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')
    try:
        # 查询新闻，用户收藏
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询数据库错误')
    if not news:
        return jsonify(errno=RET.PARAMERR, errmsg='新闻数据不存在')
    if action == 'collect':
        user.collection_news.append(news)  # 添加收藏
    else:
        user.collection_news.remove(news)  # 取消收藏
    try:
        db.session.commit()  # 提交到数据库
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()  # 数据库回退
        return jsonify(errno=RET.DBERR, errmsg='保存失败')

    # 返回成功
    return jsonify(errno=RET.OK, errmsg='OK')


# 新闻评论
@news_blu.route('/news_comment', methods=['POST'])
@user_login_data
def news_comment():
    # 校验用户是否登陆
    user = g.user
    if not user:
        return jsonify(errno=RET.USERERR, errmsg='用户未登陆')

    # 获取参数， new_id, comment, parent_id
    data_json = request.json
    news_id = data_json.get('news_id')
    comment_str = data_json.get('comment')
    parent_id = data_json.get('parent_id')
    print(parent_id)

    # 校验参数是否齐全
    if not all([news_id, comment_str]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')

    # 储存数据
    # news = None
    try:
        news = News.query.get(news_id)  # 根据新闻id返回查询对象
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询数据库失败')

    # 新闻不存在
    if not news:
        return jsonify(errno=RET.NODATA, errmsg='新闻数据不存在')

    # 添加评论信息
    comment = Comment()
    comment.content = comment_str
    comment.user_id = user.id
    comment.news_id = news.id
    if parent_id:
        comment.parent_id = parent_id

    try:
        db.session.add(comment)  # 添加新的评论
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='保存评论数据失败')

    # news_comments = news.comments
    # comments_list = []
    # for per_comment in news_comments:
    #     comments_list.append(per_comment.to_dict())
    # 返回成功
    return jsonify(errno=RET.OK, errmsg='OK', data=comment.to_dict())


# 评论点赞
@news_blu.route('/comment_like', methods=['POST'])
@user_login_data
def get_comment_like():
    # 校验是否登陆
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg='用户未登录')

    # 获取参数：comment_id, news_id, action
    data_json = request.json
    comment_id = data_json.get('comment_id')
    news_id = data_json.get('news_id')
    action = data_json.get('action')

    # 校验参数是否齐全
    if not all([comment_id, news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')

    # 校验参数是否正确
    if action not in ('add', 'remove'):
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

    # 存储数据
    try:
        # 根据评论id获取评论对象
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app(e)
        return jsonify(errno=RET.DBERR, errmsg='查询数据库错误')

    if not comment:  #  校验评论是否存在
        return jsonify(errno=RET.NODATA, errmsg='评论数据不存在')

    # 根据用户id和评论id查询是否已经点赞
    comment_like = CommentLike.query.filter_by(comment_id=comment_id, user_id=g.user.id).first()
    if action == 'add':
        if not comment_like:  # 没有点赞
            # 增加数据
            comment_like = CommentLike()
            comment_like.comment_id = comment_id
            comment_like.user_id =g.user.id
            db.session.add(comment_like)
            comment.like_count += 1  # 点赞数量+1
    else:
        if comment_like:  # 已经点赞
            db.session.delete(comment_like)  # 取消点赞
            comment.like_count -= 1  # 点赞数量-1
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='数据库查询错误')

    return jsonify(errno=RET.OK, errmsg='OK')
