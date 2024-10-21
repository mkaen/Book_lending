from flask_testing import TestCase

import pytest
from flask_login import current_user
from werkzeug.security import check_password_hash, generate_password_hash

from main import app, db, User, Book


class BaseTestCase(TestCase):

    def setUp(self):
        with app.app_context():
            db.create_all()
            db.session.add(User(first_name="Juhan",
                                last_name="Viik",
                                username="juhanv",
                                email="juhan@gmail.com",
                                password="123456",
                                duration=28))
            db.session.add(User(first_name="Priit",
                                last_name="Pätt",
                                username="priitp",
                                email="pr@gmail.com",
                                password="123456",
                                duration=28))
            db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()


class BookTestCase(BaseTestCase):

    def test_book_creation(self, client):
        client.post('/login', data={
            'username': 'juhanv',
            'password': '123456'
        }, follow_redirects=True)
        client.post('/add_book', data={
            'title': 'rich dad, poor dad',
            'author': "r. kiyosaki",
            'image_url': "https://upload.wikimedia.org/wikipedia/en/thumb/b/b9/Rich_Dad_Poor_Dad.jpg/220px"
                         "-Rich_Dad_Poor_Dad.jpg"
        })
        print(current_user.is_active)
        db.session.commit()
