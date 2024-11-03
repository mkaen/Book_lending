import pytest
from werkzeug.security import generate_password_hash

from configuration.config import TestConfig
from main import db, create_app, User, Book
from authentication import logout

app = create_app(config_class=TestConfig)
app.config['WTF_CSRF_ENABLED'] = False


@pytest.fixture
def client():
    with app.app_context():
        db.create_all()
        with app.test_client() as client:
            yield client
            logout(client)
        db.drop_all()


@pytest.fixture
def first_user_with_books(client):
    with app.app_context():
        new_user = User(first_name='Juhan',
                        last_name='viik',
                        email='juhan.viik@gmail.com',
                        username='juhanv',
                        password=generate_password_hash('123456', method='pbkdf2:sha256', salt_length=8)
                        )
        db.session.add(new_user)
        db.session.commit()
        book_1 = Book(title='Rich Dad Poor Dad',
                      author='Robert Kiyosaki',
                      image_url='https://upload.wikimedia.org/wikipedia/en/thumb/b/b9/Rich_Dad_Poor_Dad.jpg/220px'
                                '-Rich_Dad_Poor_Dad.jpg',
                      owner_id=new_user.id,
                      book_owner=new_user)
        book_2 = Book(title='Before You Quit Your Job',
                      author='Robert Kiyosaki',
                      image_url='https://m.media-amazon.com/images/I/81e59Ch9oJL._SY466_.jpg',
                      owner_id=new_user.id,
                      book_owner=new_user
                      )
        db.session.add_all([book_1, book_2])
        db.session.commit()


@pytest.fixture
def second_user_with_books(client):
    with app.app_context():
        new_user = User(first_name='Priit',
                        last_name='pätt',
                        email='priit.patt@gmail.com',
                        username='priitp',
                        password=generate_password_hash('123456', method='pbkdf2:sha256', salt_length=8)
                        )
        db.session.add(new_user)
        db.session.commit()
        book_1 = Book(title="Harry Potter and the Sorcerer's Stone",
                      author='J. K. Rowling',
                      image_url='https://m.media-amazon.com/images/I/51pg8dBgESL._SL350_.jpg',
                      book_owner=new_user,
                      owner_id=new_user.id
                      )
        book_2 = Book(title='Harry Potter and the Chamber of Secrets',
                      author='J. K. Rowling',
                      image_url='https://i.thriftbooks.com/api/imagehandler/m'
                                '/4B125D9125088953EA6F6BCF2D4EE168B5E4E8F0.jpeg',
                      book_owner=new_user,
                      owner_id=new_user.id
                      )
        db.session.add_all([book_1, book_2])
        db.session.commit()


@pytest.fixture
def add_third_user(client):
    with app.app_context():
        new_user = User(
            first_name='Toomas',
            last_name='Kruus',
            email='toomas.kruus@gmail.com',
            username='toomask',
            password=generate_password_hash('123456', method='pbkdf2:sha256', salt_length=8),
            duration=28
        )
        db.session.add(new_user)
        db.session.commit()
