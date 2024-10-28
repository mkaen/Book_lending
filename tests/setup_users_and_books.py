import pytest
from werkzeug.security import generate_password_hash

from config import TestConfig
from main import db, create_app, User

app = create_app(config_class=TestConfig)


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


@pytest.fixture
def first_user_with_books(client):
    client.post('/register', data={
        'first_name': 'Juhan',
        'last_name': 'viik',
        'email': 'juhan.viik@gmail.com',
        'username': 'juhanv',
        'password': '123456',
        'confirm_password': '123456'
    }, follow_redirects=True)
    client.post('/add_book', data={
        'title': 'Rich Dad Poor Dad',
        'author': 'Robert Kiyosaki',
        'image_url': 'https://upload.wikimedia.org/wikipedia/en/thumb/b/b9/Rich_Dad_Poor_Dad.jpg/220px-Rich_Dad_Poor_Dad.jpg'
    }, follow_redirects=True)
    client.post('/add_book', data={
        'title': 'Before You Quit Your Job',
        'author': 'Robert Kiyosaki',
        'image_url': 'https://m.media-amazon.com/images/I/81e59Ch9oJL._SY466_.jpg'
    }, follow_redirects=True)


@pytest.fixture
def second_user_with_books(client):
    client.post('/register', data={
        'first_name': 'Priit',
        'last_name': 'pätt',
        'email': 'priit.patt@gmail.com',
        'username': 'priitp',
        'password': '123456',
        'confirm_password': '123456'
    }, follow_redirects=True)
    client.post('/add_book', data={
        'title': "Harry Potter and the Sorcerer's Stone",
        'author': 'J. K. Rowling',
        'image_url': 'https://m.media-amazon.com/images/I/51pg8dBgESL._SL350_.jpg'
    }, follow_redirects=True)
    client.post('/add_book', data={
        'title': 'Harry Potter and the Chamber of Secrets',
        'author': 'J. K. Rowling',
        'image_url': 'https://i.thriftbooks.com/api/imagehandler/m/4B125D9125088953EA6F6BCF2D4EE168B5E4E8F0.jpeg'
    }, follow_redirects=True)


@pytest.fixture
def add_user(client):
    with client.application.app_context():
        new_user = User(
            first_name='Juhan',
            last_name='viik',
            email='juhan.viik@gmail.com',
            username='juhanv',
            password=generate_password_hash('123456', method='pbkdf2:sha256', salt_length=8),
            duration=28
        )
        db.session.add(new_user)
        db.session.commit()
