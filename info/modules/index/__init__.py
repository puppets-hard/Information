from flask import Blueprint

index_blu = Blueprint('index', __name__)  # 创建index蓝图对象

from . import views  # 不写的话，根据路由会找不到视图
