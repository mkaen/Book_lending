from main import db, User, Book
from setup_users_and_books import client, first_user_with_books, second_user_with_books
from authorization import login, logout


# BOOK ACTIVATION
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


#  SET USER BORROWING DURATION
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


def test_set_duration_current_user_not_allowed(client, first_user_with_books, second_user_with_books):
    login(client, 'juhanv')
    response = client.post(f'/change_duration/2', data={'duration': 12}, follow_redirects=True)
    assert response.status_code == 401


def test_set_lending_duration_not_change_borrowed_books(client, first_user_with_books, second_user_with_books):
    login(client, 'priitp')
    client.get('/reserve_book/2')
    client.get('/receive_book/2')
    book = db.get_or_404(Book, 2)
    return_date = book.return_date
    logout(client)
    login(client, 'juhanv')
    user = db.get_or_404(User, 1)
    assert user.duration == 28
    duration_response = client.post('/change_duration/1', data={'duration': 12}, follow_redirects=True)
    assert duration_response.status_code == 200
    book = db.get_or_404(Book, 2)
    assert book.return_date == return_date


def test_set_lending_duration_out_of_limit(client, first_user_with_books, second_user_with_books):
    login(client, 'juhanv')
    user = db.get_or_404(User, 1)
    assert user.duration == 28
    response_below = client.post(f'/change_duration/{user.id}', data={'duration': 0},
                                 follow_redirects=True)
    user = db.get_or_404(User, 1)
    assert user.duration == 28
    assert b"Invalid duration value" in response_below.data
    response_above = client.post(f'/change_duration/{user.id}', data={'duration': 101},
                                 follow_redirects=True)
    user = db.get_or_404(User, 1)
    assert b"Invalid duration value" in response_above.data
    assert user.duration == 28


def test_set_lending_duration_wrong_input(client, first_user_with_books, second_user_with_books):
    login(client, 'juhanv')
    user = db.get_or_404(User, 1)
    assert user.duration == 28
    response_wrong_input = client.post(f'/change_duration/{user.id}', data={'duration': 'a'},
                                       follow_redirects=True)
    user = db.get_or_404(User, 1)
    assert user.duration == 28
    assert b"Invalid duration value" in response_wrong_input.data
