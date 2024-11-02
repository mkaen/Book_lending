from flask_login import current_user
from werkzeug.security import check_password_hash

from main import db, User
from setup_users_and_books import client, first_user_with_books


def test_register_new_user(client):
    response = client.post('/register', data={
        'first_name': 'Priit',
        'last_name': 'pätt',
        'email': 'priit.patt@gmail.com',
        'username': 'priitp',
        'password': '123456',
        'confirm_password': '123456'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Your account has been created successfully." in response.data
    assert response.request.path == '/'
    result = db.session.execute(db.select(User).where(User.username == 'priitp')).first()
    user = result[0] if result else None
    assert user is not None
    assert user.first_name == 'Priit'
    assert user.last_name == 'Pätt'
    assert user.email == 'priit.patt@gmail.com'
    assert user.username == 'priitp'
    assert user.duration == 28
    assert check_password_hash(user.password, '123456')
    assert user.password != '123456'


def test_register_username_already_exists(client, first_user_with_books):
    response = client.post('/register', data={
        'first_name': 'John',
        'last_name': 'Wick',
        'email': 'john.wick@gmail.com',
        'username': 'juhanv',
        'password': '123456',
        'confirm_password': '123456'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"This username already exists." in response.data
    assert response.request.path == '/register'
    result = db.session.execute(db.select(User).where(User.email == 'john.wick@gmail.com')).first()
    user = result[0] if result else None
    assert user is None
    with client.session_transaction() as session:
        assert '_user_id' not in session


def test_register_email_already_exists(client, first_user_with_books):
    response = client.post('/register', data={
        'first_name': 'John',
        'last_name': 'Wick',
        'email': 'juhan.viik@gmail.com',
        'username': 'john_wick',
        'password': '123456',
        'confirm_password': '123456'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"This email address already exists. Try to login instead." in response.data
    assert response.request.path == '/login'
    result = db.session.execute(db.select(User).where(User.username == 'john_wick')).first()
    user = result[0] if result else None
    assert user is None
    with client.session_transaction() as session:
        assert '_user_id' not in session


def test_login_user(client, first_user_with_books):
    response = client.post('/login', data={
        'username': 'juhanv',
        'password': '123456'
    }, follow_redirects=True)
    assert current_user.first_name == 'Juhan'
    assert current_user.is_authenticated is True
    with client.session_transaction() as session:
        assert '_user_id' in session
    assert response.status_code == 200
    assert b"Logged in successfully as Juhan." in response.data
    assert response.request.path == '/'


def test_invalid_username_login(client, first_user_with_books):
    response = client.post('/login', data={
        'username': 'juhanvi',
        'password': '123456'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid Username. Please try again" in response.data
    assert response.request.path == '/login'


def test_invalid_password_login(client, first_user_with_books):
    response = client.post('/login', data={
        'username': 'juhanv',
        'password': '1234567'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid password. Please try again"
    assert response.request.path == '/login'


def test_logout_user(client, first_user_with_books):
    login_response = client.post('/login', data={
        'username': 'juhanv',
        'password': '123456'
    }, follow_redirects=True)
    assert b"Logged in successfully as Juhan." in login_response.data
    assert login_response.status_code == 200
    assert current_user.is_active is True
    logout_response = client.get('/logout', follow_redirects=True)
    assert b"You have been logged out. Hopefully we'll see you soon." in logout_response.data
    assert current_user.is_authenticated is False
    with client.session_transaction() as session:
        assert '_user_id' not in session


def test_logout_user_not_in_session(client):
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 401
