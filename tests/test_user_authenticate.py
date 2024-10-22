from flask_testing import TestCase

import pytest
from flask_login import current_user
from werkzeug.security import check_password_hash, generate_password_hash

from main import app, db, User, Book


# class Test(TestCase):
@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_book_lending.db'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()


def test_register_new_user(client):
    response = client.post('/register', data={
        'first_name': 'Juhan',
        'last_name': 'viik',
        'email': 'juhan.viik@gmail.com',
        'username': 'juhanv',
        'password': '123456',
        'confirm_password': '123456'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Your account has been created successfully." in response.data
    user = db.session.execute(db.select(User).where(User.username == 'juhanv')).scalar()
    assert user is not None
    assert user.first_name == 'Juhan'
    assert user.last_name == 'Viik'
    assert user.email == 'juhan.viik@gmail.com'
    assert user.username == 'juhanv'
    assert user.duration == 28
    assert check_password_hash(user.password, '123456')
    assert user.password != '123456'


password_hash = generate_password_hash('123456', method='pbkdf2:sha256', salt_length=8)
juhan = User(
    first_name='Juhan',
    last_name='viik',
    email='juhan.viik@gmail.com',
    username='juhanv',
    password=password_hash,
    duration=28
)


def test_login_user(client):
    with app.app_context():
        new_user = juhan
        db.session.add(new_user)
        db.session.commit()
    response = client.post('/login', data={
        'username': 'juhanv',
        'password': '123456'
    }, follow_redirects=True)
    TestCase.assertTrue(current_user.first_name, 'Juhan')
    assert new_user.is_authenticated is True
    with client.session_transaction() as session:
        assert '_user_id' in session
    assert response.status_code == 200
    assert b"Logged in successfully as Juhan." in response.data


def test_invalid_username_login(client):
    with app.app_context():
        new_user = juhan
        db.session.add(new_user)
        db.session.commit()
    response = client.post('/login', data={
        'username': 'juhanvi',
        'password': '123456'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid Username. Please try again" in response.data


def test_invalid_password_login(client):
    with app.app_context():
        new_user = juhan
        db.session.add(new_user)
        db.session.commit()
    response = client.post('/login', data={
        'username': 'juhanv',
        'password': '1234567'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid password. Please try again"


def test_logout_user(client):
    with app.app_context():
        new_user = juhan
        db.session.add(new_user)
        db.session.commit()
    login_response = client.post('/login', data={
        'username': 'juhanv',
        'password': '123456'
    }, follow_redirects=True)
    assert login_response.status_code == 200
    TestCase.assertTrue(new_user.is_active, True)
    client.get('/logout', follow_redirects=True)
    TestCase.assertFalse(new_user.is_active, False)


def test_logout_user_not_in_session(client):
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 401
