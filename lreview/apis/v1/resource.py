from flask import request, jsonify, Blueprint, g, url_for
from flask_mail import Message
from flask.views import MethodView
from lreview.models import User, Post, Image
from lreview.extensions import db, mail, photos
from lreview.apis.v1 import api_v1
from lreview.apis.v1.errors import api_abort, ValidationError
from lreview.apis.v1.auth import auth_required, generate_token, forget_token
from lreview.apis.v1.schemas import user_schema, post_schema, posts_schema
import os
import json
import hashlib
import time


class Register(MethodView):
    def post(self):
        data = json.loads(request.get_data())
        email = data['email']
        username = data['username']
        password = data['password']
        name = data['name']
        birthday = data['birthday']
        
        if User.query.filter_by(email=email).first() is not None:
            return api_abort(400, message='Existing email.', status_code=1) 
        if User.query.filter_by(username=username).first() is not None:
            return api_abort(400, message='Existing user.', status_code=2)

        user = User(email=email, username=username, name=name, birthday=birthday)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'Created.', 'status_code': 0}), 201


class Forget(MethodView):
    def post(self):
        data = json.loads(request.get_data())
        email = data['email']
            
        if User.query.filter_by(email=email).first() is None:
            return api_abort(400, message='Email not found.', status_code=1)
            
        user = User.query.filter_by(email=email).first()
        token, expiration = forget_token(user)

        msg = Message(
            subject='重設密碼',
            recipients=[email],
            html='<p>哈囉 %s :</p> \
                <p>請複製以下驗證碼以重設您的密碼</p> \
                <b>%s</b> \
                <p>請於一小時內完成密碼重置</p>' % (user.username, token)
        )
        mail.send(msg)
        return jsonify({'message': 'Token has been sent.', 'status_code': 0}), 200


class Reset(MethodView):
    decorators = [auth_required]
    
    def put(self):
        data = json.loads(request.get_data())
        password = data['password']
        user = g.current_user
        user.set_password(password)
        db.session.commit()
        return jsonify({'message': 'Modified.', 'status_code': 0}), 200


class AuthTokenAPI(MethodView):
    def post(self):
        data = json.loads(request.get_data())
        grant_type = data['grant_type']
        username = data['username']
        password = data['password']

        if grant_type is None or grant_type.lower() != 'password':
            return api_abort(code=400, message='Grant type must be password.', status_code=1)

        user = User.query.filter_by(username=username).first()
        if user is None or not user.validate_password(password):
            return api_abort(code=400, message='Username or password was invalid.', status_code=2)

        token, expiration = generate_token(user)

        response = jsonify({
            'status_code': 0,
            'access_token': token,
            'token_type': 'Bearer',
            'expires_in': expiration
        })
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Pragma'] = 'no-cache'
        return response


class UserAPI(MethodView):
    decorators = [auth_required]

    def get(self):
        user = g.current_user
        datas = user_schema(user)
        datas['status_code'] = 0
        return jsonify(datas)

    def put(self):
        data = json.loads(request.get_data())
        email = data['email']
        name = data['name']
        birthday = data['birthday']
        
        user = g.current_user
        if email != user.email and User.query.filter_by(email=email).first() is not None:
            return api_abort(400, message='Existing email.', status_code=-1) 

        user.email = email
        user.name = name
        user.birthday = birthday
        db.session.commit()
        return jsonify({'message': 'Modified.', 'status_code': 0}), 200


class Avatar(MethodView):
    decorators = [auth_required]

    def put(self):
        try:
            user = g.current_user
            filename = request.files.getlist('avatar')[0]
            name = hashlib.md5((user.username + str(time.time())).encode('UTF-8'))
            name = name.hexdigest()[:15]
            filename = photos.save(filename, name=name + '.')

            if user.avatar != 'default/defaultAvatar.png':
                path = photos.path(user.avatar)
                os.remove(path)

            user.avatar = filename
            db.session.commit()
        except:
            return api_abort(401, message='Avatar missing.', status_code=-1)
        return jsonify({'message': 'Uploaded.', 'avatar_url': photos.url(filename), 'status_code': 0}), 200 


class PostAPI(MethodView):
    decorators = [auth_required]

    def get(self, post_id):
        """Get post."""
        post = Post.query.get_or_404(post_id)
        if g.current_user != post.user:
            return api_abort(403, message='Do not touch me!!', status_code=-1)
        datas = post_schema(post)
        datas['status_code'] = 0
        return jsonify(datas)

    def put(self, post_id):
        """Edit post."""
        user = g.current_user
        post = Post.query.get_or_404(post_id)
        if user != post.user:
            return api_abort(403, message='Do not touch me!!', status_code=-1)

        title = request.form.get('title')
        body = request.form.get('body')
        happen_age = request.form.get('happen_age')
        introspection = request.form.get('introspection')
        emotion = request.form.get('emotion')
        score = request.form.get('score')
        
        post.title = title
        post.body = body
        post.happen_age = happen_age
        post.introspection = introspection
        post.emotion = emotion
        post.score = score
        db.session.commit()

        if request.files.getlist('images'):
            for filename in request.files.getlist('images'):
                name = hashlib.md5((user.username + str(time.time())).encode('UTF-8'))
                name = name.hexdigest()[:15]
                filename = photos.save(filename, name=name + '.')

                image = Image(filename=filename, post=post)
                db.session.add(image)
                db.session.commit()
        return jsonify({'message': 'Modified.', 'status_code': 0}), 200

    def delete(self, post_id):
        """Delete post."""
        post = Post.query.get_or_404(post_id)
        if g.current_user != post.user:
            return api_abort(403, message='Do not touch me!!', status_code=-1)
        for image in post.images:
            path = photos.path(image.filename)
            os.remove(path)
        db.session.delete(post)
        db.session.commit()
        return jsonify({'message': 'Deleted.', 'status_code': 0}), 200


class PostsAPI(MethodView):
    decorators = [auth_required]

    def get(self):
        # page = request.args.get('page', 1, type=int)
        # per_page = 6
        # pagination = Post.query.with_parent(g.current_user).paginate(page, per_page)
        # posts = pagination.items
        # current = url_for('.posts', page=page, _external=True)
        # prev = None
        # if pagination.has_prev:
            # prev = url_for('.posts', page=page - 1, _external=True)
        # next = None
        # if pagination.has_next:
            # next = url_for('.posts', page=page + 1, _external=True)
        # datas = posts_schema(posts, current, prev, next, pagination)
        posts = Post.query.with_parent(g.current_user)
        datas = posts_schema(posts)
        datas['status_code'] = 0
        return jsonify(datas)


    def post(self):
        user = g.current_user
        title = request.form.get('title')
        body = request.form.get('body')
        happen_age = request.form.get('happen_age')
        introspection = request.form.get('introspection')
        emotion = request.form.get('emotion')
        score = request.form.get('score')

        post = Post(title=title, body=body, happen_age=happen_age, introspection=introspection, emotion=emotion, score=score, user=user)
        db.session.add(post)
        db.session.commit()

        if request.files.getlist('images'):
            for filename in request.files.getlist('images'):
                name = hashlib.md5((user.username + str(time.time())).encode('UTF-8'))
                name = name.hexdigest()[:15]
                filename = photos.save(filename, name=name + '.')

                image = Image(filename=filename, post=post)
                db.session.add(image)
                db.session.commit()

        datas = post_schema(post)
        datas['status_code'] = 0
        response = jsonify(datas)
        response.status_code = 201
        response.headers['Location'] = url_for('.posts', post_id=post.id, _external=True)
        return response


api_v1.add_url_rule('/register', view_func=Register.as_view('register'), methods=['POST'])
api_v1.add_url_rule('/forget', view_func=Forget.as_view('forget'), methods=['POST'])
api_v1.add_url_rule('/reset', view_func=Reset.as_view('reset'), methods=['PUT'])
api_v1.add_url_rule('/oauth/token', view_func=AuthTokenAPI.as_view('token'), methods=['POST'])
api_v1.add_url_rule('/user', view_func=UserAPI.as_view('user'), methods=['GET', 'PUT'])
api_v1.add_url_rule('/user/avatar', view_func=Avatar.as_view('avatar'), methods=['PUT'])
api_v1.add_url_rule('/user/posts', view_func=PostsAPI.as_view('posts'), methods=['GET', 'POST'])
api_v1.add_url_rule('/user/post/<int:post_id>', view_func=PostAPI.as_view('post'), methods=['GET', 'PUT', 'DELETE'])
