import pytest
from config import TestConfig
from main import db, User, create_app, Book

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
        'title': 'Before you quit your job',
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


def test_users_amount_in_temporary_db(client, first_user_with_books, second_user_with_books):
    users = User.query.all()
    assert len(users) == 2


def test_books_amount_in_temporary_db(client, first_user_with_books, second_user_with_books):
    books = Book.query.all()
    assert len(books) == 4


def login(client, username: str):
    """Log in the user."""
    response = client.post('/login', data={
        'username': username,
        'password': '123456'
    }, follow_redirects=True)
    # print(f"\nLogin status code: {response.status_code}")
    # print(f"Is logged in: {current_user.is_authenticated}")
    with client.session_transaction() as session:
        print(f"\nUser id in session: {session.get('_user_id')}")
    return response


def test_add_book(client, first_user_with_books):
    """Test adding a book after login."""
    login_response = login(client, 'juhanv')
    assert login_response.status_code == 200
    response = client.post('/add_book', data={
        'title': "Rich Dad's CASHFLOW Quadrant: Rich Dad's Guide to Financial Freedom",
        'author': 'Robert Kiyosaki',
        'image_url': 'https://m.media-amazon.com/images/I/71+SWQ6xj1L._SY466_.jpg'
    }, follow_redirects=True)
    assert response.status_code == 200
    result = db.session.execute(db.select(Book).where(Book.title == "Rich Dad'S Cashflow Quadrant: Rich Dad'S Guide To "
                                                                  "Financial Freedom")).first()
    book = result[0] if result else None
    assert book is not None
    assert b"Book added successfully" in response.data
    assert book.author == 'Robert Kiyosaki'


def test_add_book_if_user_not_logged_in(client):
    """Test add_book if user not logged in."""
    response = client.post('/add_book', data={
        'title': "Rich Dad's CASHFLOW Quadrant: Rich Dad's Guide to Financial Freedom",
        'author': 'Robert Kiyosaki',
        'image_url': 'https://m.media-amazon.com/images/I/71+SWQ6xj1L._SY466_.jpg'
    }, follow_redirects=True)
    assert response.status_code == 401


def test_add_book_title_already_exists(client, first_user_with_books):
    """Test adding a book that already exists in database after login."""
    login(client, 'juhanv')
    books = db.session.query(Book).all()
    assert len(books) == 2
    response = client.post('/add_book', data={
        'title': 'Rich Dad Poor Dad',
        'author': 'Robert Kiyosaki',
        'image_url': 'https://upload.wikimedia.org/wikipedia/en/thumb/b/b9/Rich_Dad_Poor_Dad.jpg/220px'
                     '-Rich_Dad_Poor_Dad.jpg'
    }, follow_redirects=True)
    assert len(books) == 2
    assert b"A book with this title already exists." in response.data
    assert response.status_code == 200
    #  CAPITALIZED & LOWER LETTERS
    response = client.post('/add_book', data={
        'title': 'RICH dad POOR DAD',
        'author': 'Robert Kiyosaki',
        'image_url': 'https://upload.wikimedia.org/wikipedia/en/thumb/b/b9/Rich_Dad_Poor_Dad.jpg/220px'
                     '-Rich_Dad_Poor_Dad.jpg'
    }, follow_redirects=True)
    assert len(books) == 2
    assert b"A book with this title already exists." in response.data





# def test_login_user(client, first_user_with_books):
#     response = login(client, 'juhanv')
#     TestCase.assertTrue(current_user.first_name, 'Juhan')
#     assert current_user.is_authenticated is True
#     with client.session_transaction() as session:
#         assert '_user_id' in session
#     assert response.status_code == 200
#     assert b"Logged in successfully as Juhan." in response.data
