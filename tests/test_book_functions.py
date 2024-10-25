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
        'image_url': 'https://upload.wikimedia.org/wikipedia/en/thumb/b/b9/Rich_Dad_Poor_Dad.jpg/220px'
                     '-Rich_Dad_Poor_Dad.jpg'
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


def login(client, username: str):
    """Log in the user."""
    response = client.post('/login', data={
        'username': username,
        'password': '123456'
    }, follow_redirects=True)
    # print(f"\nLogin status code: {response.status_code}")
    # print(f"Is logged in: {current_user.is_authenticated}")
    # with client.session_transaction() as session:
    #     print(f"\nUser id in session: {session.get('_user_id')}")
    return response


def logout(client):
    """Log out the user."""
    response = client.get('/logout', follow_redirects=True)
    # with client.session_transaction() as session:
    #     print(f"\nUser id in session: {session.get('_user_id')}")
    return response


def test_deactivate_and_activate_for_lending(client, first_user_with_books):
    login_response = login(client, 'juhanv')
    assert login_response.status_code == 200
    activated_books = db.session.execute(
        db.session.query(Book).filter(Book.available_for_lending == True)).scalars().all()
    assert len(activated_books) == 2
    book = db.get_or_404(Book, 1)
    assert book.available_for_lending is True
    activation_response = client.get(f'/activate_to_borrow/{book.id}')
    assert b"Book Rich Dad Poor Dad is set to unavailable for lending." in activation_response.data
    updated_book = db.get_or_404(Book, 1)
    assert updated_book.available_for_lending is False
    assert activation_response.status_code == 200
    activated_books = db.session.execute(db.session.query(Book)
                                         .filter(Book.available_for_lending == True)).scalars().all()
    assert len(activated_books) == 1
    activation_response = client.get(f'/activate_to_borrow/{book.id}')
    assert b"Book Rich Dad Poor Dad is set to available for lending." in activation_response.data


def test_deactivate_for_lending_hiding_on_pages(client, first_user_with_books):
    login(client, 'juhanv')
    book = db.get_or_404(Book, 1)
    response_available_books = client.get('/available_books')
    assert b"Rich Dad Poor Dad" in response_available_books.data
    response_home_page_view = client.get('/')
    assert b"Rich Dad Poor Dad" in response_home_page_view.data
    activation_response = client.get(f'/activate_to_borrow/{book.id}')
    updated_available_books = client.get('/available_books')
    assert b"Rich Dad Poor Dad" not in updated_available_books.data
    updated_home_page_view = client.get('/')
    assert b"Rich Dad Poor Dad" not in updated_home_page_view.data
    assert activation_response.status_code == 200


def test_cannot_deactivate_book_while_book_is_lent_out(client, first_user_with_books, second_user_with_books):
    login(client, 'juhanv')
    book = db.get_or_404(Book, 4)
    assert book.available_for_lending is True
    client.get(f'/reserve_book/{book.id}')
    client.get(f'/receive_book/{book.id}')
    book = db.get_or_404(Book, 4)
    logout(client)
    login(client, 'priitp')
    client.get(f'/activate_to_borrow/{book.id}')
    updated_book = db.get_or_404(Book, 4)
    assert updated_book.available_for_lending is True


def test_deactivate_book_while_user_is_anonymous(client, first_user_with_books):
    logout(client)
    book = db.get_or_404(Book, 2)
    # with client.session_transaction() as session:
    #     print(f"\nUser id in session: {session.get('_user_id')}")
    assert book.available_for_lending is True
    response = client.get(f'/activate_to_borrow/2')
    book = db.get_or_404(Book, 2)
    assert book.available_for_lending is True
    assert response.status_code == 401


def test_cannot_deactivate_book_not_owner(client, first_user_with_books, second_user_with_books):
    login(client, 'priitp')
    book = db.get_or_404(Book, 1)
    assert book.available_for_lending is True
    response = client.get(f'/activate_to_borrow/1')
    assert response.status_code == 401
    assert book.available_for_lending is True


def test_set_lending_duration(client, first_user_with_books):
    login(client, 'juhanv')
    user = db.get_or_404(User, 1)
    assert user.duration == 28
    duration_response = client.post(f'/change_duration/{user.id}', data={'duration': 12}, follow_redirects=True)
    assert duration_response.status_code == 200
    user = db.get_or_404(User, 1)
    assert user.duration == 12
    assert b"You have successfully changed lending duration" in duration_response.data


def test_set_duration_user_anonymous(client, first_user_with_books):
    logout(client)
    # with client.session_transaction() as session:
    #     print(f"\nUser id in session: {session.get('_user_id')}")
    user = db.get_or_404(User, 1)
    assert user.duration == 28
    response = client.post(f'/change_duration/{user.id}', data={'duration': 12}, follow_redirects=True)
    assert response.status_code == 401
    assert user.duration == 28


def test_set_lending_duration_not_change_borrowed_books(client, first_user_with_books, second_user_with_books):
    login(client, 'priitp')
    book = db.get_or_404(Book, 2)
    client.get(f'/reserve_book/{book.id}')
    client.get(f'/receive_book/{book.id}')
    return_date = book.return_date
    logout(client)
    login(client, 'juhanv')
    user = db.get_or_404(User, 1)
    assert user.duration == 28
    duration_response = client.post(f'/change_duration/{user.id}', data={'duration': 12}, follow_redirects=True)
    assert duration_response.status_code == 200
    assert book.return_date == return_date


def test_search_books_by_author(client, first_user_with_books, second_user_with_books):
    logout(client)
    response = client.get('/searchbar/?query=kiyosaki', follow_redirects=True)
    assert response.status_code == 200
    assert b"Rich Dad Poor Dad" in response.data
    assert b"Before You Quit Your Job" in response.data
    assert b"Harry Potter and the Sorcerer's Stone" not in response.data
    assert b"Harry Potter and the Chamber of Secrets" not in response.data


def test_search_books_by_title(client, first_user_with_books, second_user_with_books):
    logout(client)
    response = client.get('/searchbar/?query=potter', follow_redirects=True)
    assert response.status_code == 200
    assert b"Harry Potter and the Sorcerer's Stone" in response.data
    assert b"Harry Potter and the Chamber of Secrets" in response.data
    assert b"Rich Dad Poor Dad" not in response.data
    assert b"Before You Quit Your Job" not in response.data


def test_search_books_blank_input(client, first_user_with_books, second_user_with_books):
    logout(client)
    response = client.get('/searchbar/?query= ', follow_redirects=True)
    assert response.status_code == 200
    assert b"Wrong input" in response.data
    assert b"Harry Potter and the Sorcerer's Stone" not in response.data
    assert b"Harry Potter and the Chamber of Secrets" not in response.data
    assert b"Rich Dad Poor Dad" not in response.data
    assert b"Before You Quit Your Job" not in response.data
