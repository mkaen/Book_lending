import unittest
from unittest import TestCase
from main import app, db, User, Book
from flask_login import current_user


class BaseTestCase(TestCase):
    """A Base test case."""
    def create_app(self):
        app.config.from_object('config.TestConfig')
        return app

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


class FlaskTestCase(BaseTestCase):
    """Flask test case."""
    def test_index(self):
        response = current_user.get('/login', content_type='html/text')
        self.assertEqual(response.status_code, 200)
