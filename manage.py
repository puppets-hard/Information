# from flask import current_app
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from info import create_app, db
from info import models

app = create_app("development")

manager = Manager(app)  # 把Manager类和应用程序实例进行关联
Migrate(app, db)  # 绑定 数据库与app,建立关系
# Flask-Migrate提供了一个MigrateCommand类，可以附加到flask-script的manager对象上
# manager是Flask-Script的实例，这条语句在flask-Script中添加一个db命令
manager.add_command('db', MigrateCommand)


if __name__ == '__main__':
    # app.run()  使用flask_script后，这个地方要改，不然python manage.py db init时候会变成开启服务器
    manager.run()
