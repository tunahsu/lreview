from flask import request, jsonify, Blueprint, g, url_for
from flask_mail import Message
from flask.views import MethodView
from lreview.models import User, Post
from lreview.extensions import db, mail
from lreview.apis.v1 import api_v1
from lreview.apis.v1.errors import api_abort, ValidationError
from lreview.apis.v1.auth import auth_required, generate_token, forget_token
from lreview.apis.v1.schemas import user_schema, post_schema, posts_schema
import json


class Register(MethodView):
    def post(self):
        data = json.loads(request.get_data())

        try:
            email = data['email']
            username = data['username']
            password = data['password']
            name = data['name']
            birthday = data['birthday']
        except:
            return api_abort(400, message='Missing arguments.')
        
        if str(email).strip() == '' or str(username).strip() == '' or str(password).strip() == '' or str(name).strip() == '' or str(birthday).strip() == '':
            return api_abort(400, message='Missing arguments.')
        if User.query.filter_by(email=email).first() is not None:
            return api_abort(400, message='Existing email.') 
        if User.query.filter_by(username=username).first() is not None:
            return api_abort(400, message='Existing user.')

        user = User(email=email, username=username, name=name, birthday=birthday)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'Created.'}), 201


class Forget(MethodView):
    def post(self):
        data = json.loads(request.get_data())
        email = data['email']
        user = User.query.filter_by(email=email).first()

        if user is None:
            return api_abort(400, message='Email not found.')
            
        token, expiration = forget_token(user)

        msg = Message(
            subject='重設密碼',
            recipients=[email],
            html='<h2>哈囉 %s</h2> \
                <h2>請複製以下驗證碼以重設您的密碼</h2> \
                <h3>%s</h3> \
                <h2>請於一小時內完成密碼重置</h2>' % (user.username, token)
        )
        mail.send(msg)
        return jsonify({'message': 'Token has been sent.'}), 200


class Reset(MethodView):
    decorators = [auth_required]
    
    def post(self):
        data = json.loads(request.get_data())
        password = data['password']
        user = g.current_user

        if password is None:
            return api_abort(400, message='Missing arguments.')

        user.set_password(password)
        db.session.commit()
        return jsonify({'message': 'Modified.'}), 200


class AuthTokenAPI(MethodView):
    def post(self):
        data = json.loads(request.get_data())
        grant_type = data['grant_type']
        username = data['username']
        password = data['password']

        if grant_type is None or grant_type.lower() != 'password':
            return api_abort(code=400, message='Grant type must be password.')

        user = User.query.filter_by(username=username).first()
        if user is None or not user.validate_password(password):
            return api_abort(code=400, message='Username or password was invalid.')

        token, expiration = generate_token(user)

        response = jsonify({
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
        return jsonify(user_schema(g.current_user))


class PostAPI(MethodView):
    decorators = [auth_required]

    def get(self, post_id):
        """Get post."""
        post = Post.query.get_or_404(post_id)
        if g.current_user != post.user:
            return api_abort(403)
        return jsonify(post_schema(post))

    def put(self, post_id):
        """Edit post."""
        post = Post.query.get_or_404(post_id)
        if g.current_user != post.user:
            return api_abort(403)

        data = json.loads(request.get_data())

        try:
            title = data['title']
            body = data['body']
            happen_age = data['happen_age']
            introspection = data['introspection']
            emotion = data['emotion']
            score = data['score']
        except:
            raise ValidationError('Content was empty or invalid.')

        if str(title).strip() == '' or str(body).strip() == '' or str(happen_age).strip() == '' \
        or str(introspection).strip() == '' or str(score).strip() == '' or str(emotion).strip() == '':
            raise ValidationError('Content was empty or invalid.')
        
        post.title = title
        post.body = body
        post.happen_age = happen_age
        post.introspection = introspection
        post.emotion = emotion
        post.score = score
        db.session.commit()
        return '', 204

    def delete(self, post_id):
        """Delete post."""
        post = Post.query.get_or_404(post_id)
        if g.current_user != post.user:
            return api_abort(403)
        db.session.delete(post)
        db.session.commit()
        return '', 204


class PostsAPI(MethodView):
    decorators = [auth_required]

    def get(self):
        page = request.args.get('page', 1, type=int)
        per_page = 6
        pagination = Post.query.with_parent(g.current_user).paginate(page, per_page)
        posts = pagination.items
        current = url_for('.posts', page=page, _external=True)
        prev = None
        if pagination.has_prev:
            prev = url_for('.posts', page=page - 1, _external=True)
        next = None
        if pagination.has_next:
            next = url_for('.posts', page=page + 1, _external=True)
        return jsonify(posts_schema(posts, current, prev, next, pagination))

    def post(self):
        data = json.loads(request.get_data())

        try:
            title = data['title']
            body = data['body']
            happen_age = data['happen_age']
            introspection = data['introspection']
            emotion = data['emotion']
            score = data['score']
        except:
            raise ValidationError('Content was empty or invalid.')

        if str(title).strip() == '' or str(body).strip() == '' or str(happen_age).strip() == '' \
        or str(introspection).strip() == '' or str(emotion).strip() == '' or str(score).strip() == '':
            raise ValidationError('Content was empty or invalid.')

        post = Post(title=title, body=body, happen_age=happen_age, introspection=introspection, emotion=emotion, score=score, user=g.current_user)
        db.session.add(post)
        db.session.commit()
        response = jsonify(post_schema(post))
        response.status_code = 201
        response.headers['Location'] = url_for('.posts', post_id=post.id, _external=True)
        return response


api_v1.add_url_rule('/register', view_func=Register.as_view('register'), methods=['POST'])
api_v1.add_url_rule('/forget', view_func=Forget.as_view('forget'), methods=['POST'])
api_v1.add_url_rule('/reset', view_func=Reset.as_view('reset'), methods=['POST'])
api_v1.add_url_rule('/oauth/token', view_func=AuthTokenAPI.as_view('token'), methods=['POST'])
api_v1.add_url_rule('/user', view_func=UserAPI.as_view('user'), methods=['GET'])
api_v1.add_url_rule('/user/posts', view_func=PostsAPI.as_view('posts'), methods=['GET', 'POST'])
api_v1.add_url_rule('/user/post/<int:post_id>', view_func=PostAPI.as_view('post'), methods=['GET', 'PUT', 'DELETE'])
