from flask import request, jsonify, Blueprint, g, url_for
from flask.views import MethodView
from lreview.models import User, Post
from lreview.extensions import db
from lreview.apis.v1 import api_v1
from lreview.apis.v1.errors import api_abort, ValidationError
from lreview.apis.v1.auth import auth_required, generate_token
from lreview.apis.v1.schemas import user_schema, post_schema, posts_schema


def get_post_body():
    data = request.get_json()
    body = data.get('body')
    if body is None or str(body).strip() == '':
        raise ValidationError('The post body was empty or invalid.')
    return body


class Register(MethodView):
    def post(self):
        email = request.json.get('email')
        username = request.json.get('username')
        password = request.json.get('password')
        name = request.json.get('name')
        birthday = request.json.get('birthday')
        if email is None or username is None or password is None or name is None or birthday is None:
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

class AuthTokenAPI(MethodView):
    def post(self):
        grant_type = request.json.get('grant_type')
        username = request.json.get('username')
        password = request.json.get('password')

        if grant_type is None or grant_type.lower() != 'password':
            return api_abort(code=400, message='The grant type must be password.')

        user = User.query.filter_by(username=username).first()
        if user is None or not user.validate_password(password):
            return api_abort(code=400, message='Either the username or password was invalid.')

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


class PostsAPI(MethodView):
    decorators = [auth_required]

    def get(self):
        page = request.args.get('page', 1, type=int)
        per_page = 5
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
        post = Post(body=get_post_body(), user=g.current_user)
        db.session.add(post)
        db.session.commit()
        response = jsonify(post_schema(post))
        response.status_code = 201
        response.headers['Location'] = url_for('.posts', post_id=post.id, _external=True)
        return response


api_v1.add_url_rule('/register', view_func=Register.as_view('register'), methods=['POST'])
api_v1.add_url_rule('/oauth/token', view_func=AuthTokenAPI.as_view('token'), methods=['POST'])
api_v1.add_url_rule('/user', view_func=UserAPI.as_view('user'), methods=['GET'])
api_v1.add_url_rule('/user/posts', view_func=PostsAPI.as_view('posts'), methods=['GET', 'POST'])