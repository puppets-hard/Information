import random
import re
from datetime import datetime

from flask import request, make_response, current_app, jsonify, session

from info.models import User
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET
from info import redis_store, constants, db

from . import passport_blu


@passport_blu.route("/image_code", methods=["GET"])
def image_code():
    # 获取查询字符串code_id，虽然在生成图片验证码的时候不需要用到，但是在存到redis中需要识别出是哪个
    code_id = request.args.get('code_id')  # 这个值一定要传，不然因为为None导致存储失败
    # 生成图片验证码，验证码，名字
    name, text, image = captcha.generate_captcha()
    print(text)

    try:
        # 将验证码信息存入redis中,setex的参数分别是，key，有效期，value
        redis_store.setex('ImageCode_'+code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)
    except Exception as e:
        # current_app输出log
        current_app.logger.error(e)
        return make_response(jsonify(errno=RET.DATAERR, errmsg='保存图片验证码失败'))
    # 返回图片验证码响应
    resp = make_response(image)
    resp.headers["Content-Type"] = 'image/jpg'  # 将http的Content-Type的值设为图片
    return resp


@passport_blu.route("/sms_code", methods=["POST"])
def sms_code():
    param_dict = request.json
    type(param_dict)
    mobile = param_dict.get('mobile')

    image_code = param_dict.get('image_code')
    print("输入的图片验证码类型", type(image_code))
    image_code_id = param_dict.get('image_code_id')

    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')

    if not re.match('^1[3578][0-9]{9}$', mobile):
        return jsonify(errno=RET.DATAERR, errmsg='手机号不正确')

    try:
        real_image_code = redis_store.get('ImageCode_'+image_code_id)
        print("图片验证码类型：", type(real_image_code))
        if real_image_code:
            real_image_code = real_image_code.decode()
            redis_store.delete('ImageCode_'+image_code_id)

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='获取图片验证码失败')

    if not real_image_code:
        return jsonify(errno=RET.NODATA, errmsg='验证码已过期')

    if image_code.lower() != real_image_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg='验证码输入错误')

    try:
        user = User.query.filter_by(mobile=mobile).first()

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库查询错误')

    if user:
        return jsonify(errno=RET.DATAEXIST, errmsg='该手机已被注册')

    result = random.randint(0, 999999)
    sms_code = '%06d' % result

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


@passport_blu.route("/register", methods=["POST"])
def register():
    # 获取手机号，短信验证码，密码
    json_data = request.json
    mobile = json_data.get('mobile')
    sms_code = json_data.get('smscode')
    print(sms_code)
    print(type(sms_code))
    password = json_data.get('password')
    # 校验参数是否完整
    if not all([mobile, sms_code, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    # 校验短信验证码是否正确
    try:
        real_sms_code = redis_store.get('SMS_' + mobile)
        real_sms_code = real_sms_code.decode()

        print(real_sms_code)
        print(type(real_sms_code))

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='获取本地验证码失败')

    if not real_sms_code:
        return jsonify(errno=RET.NODATA, errmsg='验证码过期')

    if sms_code != real_sms_code:
        return jsonify(errno=RET.DATAERR, errmsg='验证码错误')

    try:
        redis_store.delete('SMS_' + mobile)
    except Exception as e:
        current_app.logger.error(e)

    # 保存用户信息
    user = User()
    user.nick_name = mobile
    user.mobile = mobile
    user.password = password

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.loggert(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库保存错误')

    # 保存用户状态
    session['user_id'] = user.id
    session['nick_name'] = user.nick_name
    session['mobile'] = user.mobile

    return jsonify(errno=RET.OK, errmsg='OK')


@passport_blu.route("/login", methods=["POST"])
def login():
    # 获取手机号，密码参数
    json_data = request.json
    mobile = json_data.get('mobile')
    password = json_data.get('password')

    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")
    # 校验账号名是否存在
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='数据库查询错误')

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


@passport_blu.route("/logout", methods=["post"])
def logout():
    # 清楚用户登陆信息
    session.pop('user_id', None)
    session.pop('nick_name', None)
    session.pop('mobile', None)
    return jsonify(errno=RET.OK, errmsg='OK')