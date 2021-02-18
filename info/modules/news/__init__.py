from flask import Blueprint

news_blu = Blueprint('news', __name__)

from . import views
