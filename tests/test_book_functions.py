import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

from main import app, db, Book, User
from flask_login import login_user, current_user, LoginManager


@pytest.fixture
def client():
    """Set up the test client and initialize the database."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()


@pytest.fixture
def init_database():
    """Initialize the test database with two users."""
    user_1 = User(first_name="Juhan",
                  last_name="Viik",
                  username="juhanv",
                  email="juhan@gmail.com",
                  password=generate_password_hash("password123", method='pbkdf2:sha256', salt_length=8),
                  duration=28)
    user_2 = User(first_name="Priit",
                  last_name="Pätt",
                  username="priitp",
                  email="pr@gmail.com",
                  password=generate_password_hash("password123", method='pbkdf2:sha256', salt_length=8),
                  duration=28)
    db.session.add_all([user_1, user_2])
    db.session.commit()


def login(client):
    """Log in the user with the test client."""
    response = client.post('/login', data={'username': "juhanv", 'password': "password123"}, follow_redirects=True)
    print(f"\nLogin status code: {response.status_code}")
    print(f"Is logged in: {current_user.is_authenticated}")
    return response


def test_create_new_book(client, init_database):
    """Test the creation of a new book."""
    login_response = login(client)
    assert login_response.status_code == 200
    assert client
    response = client.post('/add_book', data={
        'title': 'rich dad, poor dad',
        'author': "r. kiyosaki",
        'image_url': "https://upload.wikimedia.org/wikipedia/en/thumb/b/b9/Rich_Dad_Poor_Dad.jpg/220px"
                     "-Rich_Dad_Poor_Dad.jpg"
    }, follow_redirects=True)
    # print(f"----------- {response.data}----------")
    assert response.status_code == 200
    with app.app_context():
        added_book = db.session.execute(db.select(Book).where(Book.title == "Rich Dad, Poor Dad")).scalar_one_or_none()
        assert added_book is not None
        assert added_book.author == 'Rich Dad, Poor Dad'
        assert added_book.image_url == ('https://upload.wikimedia.org/wikipedia/en/thumb/b/b9/Rich_Dad_Poor_Dad.jpg'
                                        '/220px-Rich_Dad_Poor_Dad.jpg')
