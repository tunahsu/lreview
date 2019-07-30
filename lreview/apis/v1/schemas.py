from flask import url_for
from lreview.models import Post


def user_schema(user):
    return {
        'id': user.id,
        'username': user.username,
    }


def post_schema(post):
    return {
        'id': post.id,
        'kind': 'Post',
        'body': post.body,
        'user': {
            'username': post.user.username,
            'kind': 'User',
        },
    }


def posts_schema(posts, current, prev, next, pagination):
    return {
        'self': current,
        'kind': 'PostCollection',
        'posts': [post_schema(post) for post in posts],
        'prev': prev,
        'last': url_for('.posts', page=pagination.pages, _external=True),
        'first': url_for('.posts', page=1, _external=True),
        'next': next,
        'count': pagination.total
    }
