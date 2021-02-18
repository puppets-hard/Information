import random
import re
from datetime import datetime

from flask import request, make_response, current_app, jsonify, session

from info.models import User
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET
from info import redis_store, constants, db

from . import passport_blu


# 请求验证码图片
@passport_blu.route("/image_code", methods=["GET"])
def image_code():
    # 获取查询字符串code_id，虽然在生成图片验证码的时候不需要用到，但是在存到redis中需要识别出是哪个
    code_id = request.args.get('code_id')  # 这个值一定要传，不然因为为None导致存储失败
    # 利用验证码工具，生成图片验证码，验证码，名字
    name, text, image = captcha.generate_captcha()
    print(text)

    try:
        # 将验证码信息存入redis中,setex的参数分别是，key，有效期，value
        redis_store.setex('ImageCode_'+code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)
    except Exception as e:
        # current_app输出log
        current_app.logger.error(e)
        # 返回一个图片响应
        # 这个函数一般用于返回有响应体头的响应
        return make_response(jsonify(errno=RET.DATAERR, errmsg='保存图片验证码失败'))
    # 返回图片验证码响应
    resp = make_response(image)
    # 添加请求头
    resp.headers["Content-Type"] = 'image/jpg'  # 将http的Content-Type的值设为图片
    return resp


# 获取短信验证码
@passport_blu.route("/sms_code", methods=["POST"])
def sms_code():
    # 获取json格式的数据
    param_dict = request.json
    # print(param_dict)
    # print(param_dict['mobile'])  # 这种方式也能取出来
    # print("json格式的数据类型：", type(param_dict))

    # 从json中获取手机号
    mobile = param_dict.get('mobile')
    # 从json中获取图片验证码
    image_code = param_dict.get('image_code')
    print("输入的图片验证码类型：", type(image_code))
    image_code_id = param_dict.get('image_code_id')

    # 校验参数是否齐全
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')

    # 校验手机号格式
    if not re.match('^1[3578][0-9]{9}$', mobile):
        return jsonify(errno=RET.DATAERR, errmsg='手机号不正确')

    try:
        # 从数据库中取出图片验证码
        real_image_code = redis_store.get('ImageCode_'+image_code_id)
        # print("图片验证码类型：", type(real_image_code))
        if real_image_code:
            # 从redis取出来的str是二进制类型的，所以要转换字符
            real_image_code = real_image_code.decode()
            # 从redis中删除已经提取了的数据
            redis_store.delete('ImageCode_'+image_code_id)
    except Exception as e:
        # 在日志中记录错误信息
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='获取图片验证码失败')

    # 如果在redis中没有找到数据，返回验证码过期
    if not real_image_code:
        return jsonify(errno=RET.NODATA, errmsg='验证码已过期')

    # 校验图片验证码
    if image_code.lower() != real_image_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg='验证码输入错误')

    try:
        # 在数据库中尝试查找该用户是否存在
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库查询错误')

    # 校验手机号是否被注册
    if user:
        return jsonify(errno=RET.DATAEXIST, errmsg='该手机已被注册')

    # 0-999999的整数验证码
    result = random.randint(0, 999999)
    sms_code = '%06d' % result  # 将整数验证码转换成6位的str
    current_app.logger.debug('短信验证码的内容：%s' % sms_code)

    # TODO 发送短信
    print(sms_code)
    print(type(sms_code))

    try:
        # set方法的参数分别为：key， value，有效期
        redis_store.set('SMS_'+mobile, sms_code, constants.SMS_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='保存验证码失败')

    return jsonify(errno=RET.OK, errmsg='发送成功')


# 注册
@passport_blu.route("/register", methods=["POST"])
def register():
    # 获取手机号，短信验证码，密码
    json_data = request.json
    mobile = json_data.get('mobile')
    sms_code = json_data.get('smscode')
    password = json_data.get('password')
    # 校验参数是否完整
    if not all([mobile, sms_code, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    try:
        real_sms_code = redis_store.get('SMS_' + mobile)  # 数据类型：bytes
        real_sms_code = real_sms_code.decode()  # 数据类型：str
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='获取本地验证码失败')

    # 校验短信验证码是否过期
    if not real_sms_code:
        return jsonify(errno=RET.NODATA, errmsg='验证码过期')

    # 校验短信验证码是否正确
    if sms_code != real_sms_code:
        return jsonify(errno=RET.DATAERR, errmsg='验证码错误')

    try:
        # 删除奇景获取了的验证码
        redis_store.delete('SMS_' + mobile)
    except Exception as e:
        current_app.logger.error(e)

    # 保存用户信息
    user = User()  # 创建模型类对象
    # 添加数据
    user.nick_name = mobile
    user.mobile = mobile
    user.password = password

    try:
        # 插入一条新对象
        db.session.add(user)
        db.session.commit()  # 提交到数据库
    except Exception as e:
        current_app.loggert(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库保存错误')

    # 记录最后一次登陆时间
    try:
        user.last_login = datetime.now()
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)

    # 用session保存用户状态
    session['user_id'] = user.id
    session['nick_name'] = user.nick_name
    session['mobile'] = user.mobile

    return jsonify(errno=RET.OK, errmsg='OK')


# 登陆
@passport_blu.route("/login", methods=["POST"])
def login():
    # 获取手机号，密码参数
    json_data = request.json
    mobile = json_data.get('mobile')
    password = json_data.get('password')

    # 校验参数是否完整
    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    try:
        # 尝试查询该手机号在数据库是否存在
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库查询错误')

    # 校验账号名是否存在
    if not user:
        return jsonify(errno=RET.USERERR, errmsg='用户不存在')

    # 校验密码是否正确
    if not user.check_password(password):
        return jsonify(errno=RET.PWDERR, errmsg='密码错误')

    # 保存用户状态
    session['user_id'] = user.id
    session['nick_name'] = user.nick_name
    session['mobile'] = user.mobile

    # 记录最后一次登陆时间
    try:
        user.last_login = datetime.now()
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)

    # 返回成功
    return jsonify(errno=RET.OK, errmsg='OK')


# 登出
@passport_blu.route("/logout", methods=["post"])
def logout():
    # 清除用户登陆信息
    session.pop('user_id', None)
    session.pop('nick_name', None)
    session.pop('mobile', None)
    # 返回json数据
    return jsonify(errno=RET.OK, errmsg='OK')