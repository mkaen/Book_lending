from main import db, User, Book
from setup_users_and_books import client, first_user_with_books, second_user_with_books
from authentication import login


def test_users_amount_in_temporary_db(client, first_user_with_books, second_user_with_books):
    users = User.query.all()
    assert len(users) == 2


def test_books_amount_in_temporary_db(client, first_user_with_books, second_user_with_books):
    books = Book.query.all()
    assert len(books) == 4


def test_validate_book_ownership(client, first_user_with_books, second_user_with_books):
    result_rich_dad = db.session.execute(db.select(Book).where(Book.title == 'Rich Dad Poor Dad')).first()
    book_rich_dad = result_rich_dad[0] if result_rich_dad else None
    assert book_rich_dad.owner_id == 1
    result_hp = db.session.execute(db.select(Book).where(Book.title == "Harry Potter and the Sorcerer's Stone")).first()
    book_hp = result_hp[0] if result_hp else None
    assert book_hp.owner_id == 2
    book_owner = db.get_or_404(User, 2)
    assert book_owner.first_name == 'Priit'


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
    assert response.request.path == "/"
    result = db.session.execute(db.select(Book).where(Book.title == "Rich Dad's CASHFLOW Quadrant: Rich Dad's Guide "
                                                                    "to Financial Freedom")).first()
    book = result[0] if result else None
    assert book is not None
    #  VALIDATE FLASH MESSAGE
    assert b"Book added successfully" in response.data

    assert book.author == 'Robert Kiyosaki'
    #  VALIDATE REDIRECT
    assert response.request.path == "/"


def test_add_book_user_not_authenticated(client):
    """Test add_book if user not logged in."""
    response = client.post('/add_book', data={
        'title': "Rich Dad's CASHFLOW Quadrant: Rich Dad's Guide to Financial Freedom",
        'author': 'Robert Kiyosaki',
        'image_url': 'https://m.media-amazon.com/images/I/71+SWQ6xj1L._SY466_.jpg'
    }, follow_redirects=True)
    assert response.status_code == 401
    assert response.request.path == "/add_book"


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
        'author': 'Robert kiyosaki',
        'image_url': 'https://upload.wikimedia.org/wikipedia/en/thumb/b/b9/Rich_Dad_Poor_Dad.jpg/220px'
                     '-Rich_Dad_Poor_Dad.jpg'
    }, follow_redirects=True)
    assert len(books) == 2
    assert b"A book with this title already exists." in response.data
    assert response.request.path == '/add_book'


def test_add_book_author_name_too_short(client, first_user_with_books):
    login(client, "juhanv")
    response = client.post('/add_book', data={
        'title': 'Rich Dad Poor Dad',
        'author': 'R K',
        'image_url': 'https://upload.wikimedia.org/wikipedia/en/thumb/b/b9/Rich_Dad_Poor_Dad.jpg/220px'
                     '-Rich_Dad_Poor_Dad.jpg'
    }, follow_redirects=True)
    assert b"Field must be at least 4 characters long." in response.data
    assert response.request.path == '/add_book'
    books = db.session.query(Book).all()
    assert len(books) == 2


def test_add_book_wrong_url(client, first_user_with_books):
    login(client, "juhanv")
    response = client.post('/add_book', data={
        'title': 'Rich Dad Poor Dad',
        'author': 'R K',
        'image_url': 'https://upload.wikimedia.org/wikipedia'
    }, follow_redirects=True)
    assert b"Image URL is not valid. Please try again."
    assert response.request.path == '/add_book'
