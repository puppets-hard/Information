import random
import re

from flask import request, make_response, current_app, jsonify

from info.models import User
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET
from info import redis_store, constants
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
        return make_response(jsonify(errno=RET.DATAERR, errmsg='保存图片失败'))
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
    image_code_id = param_dict.get('image_code_id')

    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')

    if not re.match('^1[3578][0-9]{9}$', mobile):
        return jsonify(errno=RET.DATAERR, errmsg='手机号不正确')

    try:
        real_image_code = redis_store.get('ImageCode_'+image_code_id)
        type(real_image_code)
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

    try:
        # set方法的参数分别为：key， value，有效期
        redis_store.set('SMS_'+mobile, sms_code, constants.SMS_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='保存验证码失败')


    return jsonify(errno=RET.OK, errmsg='发送成功')


@passport_blu.route("/register", methods=["POST"])
def register():
    pass


@passport_blu.route("/login", methods=["POST"])
def login():
    pass


@passport_blu.route("/logout", methods=["post"])
def logout():
    pass