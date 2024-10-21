import unittest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

from main import app, db, Book, User
from flask_login import login_user


class TestCase(unittest.TestCase):

    def setUp(self):
        """Set up environment to run before every test."""
        # Kasutame testirežiimi ja loome rakenduse ja testiklienti
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()

        self.user_1 = User(first_name="Juhan",
                           last_name="Viik",
                           username="juhanv",
                           email="juhan@gmail.com",
                           password=generate_password_hash("password123", method='pbkdf2:sha256', salt_length=8),
                           duration=28)
        db.session.add(self.user_1)
        db.session.commit()
        self.user_2 = User(first_name="Priit",
                           last_name="Pätt",
                           username="priitp",
                           email="pr@gmail.com",
                           password=generate_password_hash("password123", method='pbkdf2:sha256', salt_length=8),
                           duration=28)
        db.session.add(self.user_2)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login(self):
        """Login User."""
        with self.app:
            self.app.post('/login', data=dict(username="juhanv", password="password123"))

    def test_create_new_book(self):
        self.login()
        new_book_data = {'title': 'rich dad, poor dad',
                         'author': "r. kiyosaki",
                         'image_url': "https://upload.wikimedia.org/wikipedia/en/thumb/b/b9/Rich_Dad_Poor_Dad.jpg/220px"
                                      "-Rich_Dad_Poor_Dad.jpg"}
        response = self.app.post('/add_book', data=new_book_data, follow_redirects=True)
        self.assertEqual(200, response.status_code)


if __name__ == '__main__':
    unittest.main()
