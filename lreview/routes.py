from flask import request
from lreview.models import User, Post, Category
from lreview.extensions import db


@app.route('/api/register', methods=['POST'])
def register():
    print('hi')
    username = request.json.get('username')
    password = request.json.get('password')
    if username is None or password is None:
        abort(400)  # missing arguments
    if User.query.filter_by(username=username).first() is not None:
        abort(400)  # existing user
    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'username': user.username}), 201
