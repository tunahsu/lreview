from flask import url_for
from lreview.models import Post


def user_schema(user):
    return {
        'kind': 'User',
        'id': user.id,
        'username': user.username,
        'name': user.name,
        'self': url_for('.user', _external=True),
        'posts_url': url_for('.posts', _external=True),
        'posts_count': user.posts.count()
    }


def post_schema(post):
    return {
        'kind': 'Post',
        'id': post.id,
        'self': url_for('.post', post_id=post.id, _external=True),
        'title': post.title,
        'body': post.body,
        'happen_age': post.happen_age,
        'introspection': post.introspection,
        'emotion': post.emotion,
        'score': post.score,
        'user': {
            'kind': 'User',
            'id': post.user.id,
            'url': url_for('.user', _external=True),
            'username': post.user.username
        }
    }


def posts_schema(posts):
    return {
        'kind': 'PostCollection',
        'posts': [post_schema(post) for post in posts],
        # 'first': url_for('.posts', page=1, _external=True),
        # 'last': url_for('.posts', page=pagination.pages, _external=True),
        'self': url_for('.posts', _external=True),
        # 'prev': prev,
        # 'next': next,
        'count': posts.count()
    }
