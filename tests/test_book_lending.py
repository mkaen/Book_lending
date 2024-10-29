from flask_login import current_user

from main import db, User, Book
from setup_users_and_books import client, first_user_with_books, second_user_with_books, add_third_user
from authorization import login, logout


# RESERVATION
def test_reserve_book(client, first_user_with_books, second_user_with_books):
    login(client, 'juhanv')
    book = db.get_or_404(Book, 3)
    assert not book.reserved
    response = client.get('/reserve_book/3', follow_redirects=True)
    book = db.get_or_404(Book, 3)
    assert response.status_code == 200
    assert book.reserved


def test_reserve_book_not_found(client, first_user_with_books):
    login(client, 'juhanv')
    response = client.get('/reserve_book/3', follow_redirects=True)
    assert response.status_code == 404


def test_reserve_book_already_reserved(client, first_user_with_books, second_user_with_books, add_third_user):
    login(client, 'toomask')
    response = client.get('/reserve_book/1', follow_redirects=True)
    book = db.get_or_404(Book, 1)
    assert response.status_code == 200
    assert book.reserved
    assert book.lender_id == 3
    logout(client)
    login(client, 'priitp')
    client.get('/reserve_book/1', follow_redirects=True)
    updated_book = db.get_or_404(Book, 1)
    assert updated_book.lender_id != current_user.id


def test_reserve_book_user_not_authorized(client, first_user_with_books):
    logout(client)
    response = client.get('/reserve_book/1', follow_redirects=True)
    assert response.status_code == 401


def test_reserve_book_reserve_own_book(client, first_user_with_books):
    login(client, 'juhanv')
    book = db.get_or_404(Book, 1)
    assert not book.reserved
    response = client.get(f'/reserve_book/{book.id}', follow_redirects=True)
    updated_book = db.get_or_404(Book, 1)
    assert response.status_code == 200
    assert b"You cannot reserve your own book!" in response.data
    assert not updated_book.reserved


#  BOOK CANCELLATION
def test_cancel_reservation_by_owner(client, first_user_with_books, add_third_user):
    login(client, 'toomask')
    reservation_response = client.get('/reserve_book/1', follow_redirects=True)
    assert reservation_response.status_code == 200
    book = db.get_or_404(Book, 1)
    assert book.reserved
    assert book.lender_id == 2
    logout(client)
    login(client, 'juhanv')
    cancel_response = client.get(f'/cancel_reservation/{book.id}', follow_redirects=True)
    updated_book = db.get_or_404(Book, 1)
    assert cancel_response.status_code == 200
    assert b'Book "Rich Dad Poo Dad" reservation is successfully cancelled'
    assert not updated_book.reserved
    assert not updated_book.lender_id


def test_cancel_reservation_by_lender(client, first_user_with_books, add_third_user):
    login(client, 'toomask')
    reservation_response = client.get('/reserve_book/1', follow_redirects=True)
    assert reservation_response.status_code == 200
    book = db.get_or_404(Book, 1)
    assert book.reserved
    cancel_response = client.get(f'/cancel_reservation/{book.id}', follow_redirects=True)
    updated_book = db.get_or_404(Book, 1)
    assert cancel_response.status_code == 200
    assert not updated_book.reserved
    assert b'Book "Rich Dad Poo Dad" reservation is successfully cancelled'


def test_cancel_reservation_by_unauthenticated_user(client, first_user_with_books):
    logout(client)
    reservation_response = client.get('/cancel_reservation/1', follow_redirects=True)
    assert reservation_response.status_code == 401


def test_cancel_reservation_by_unauthorized_user(client, first_user_with_books, second_user_with_books, add_third_user):
    login(client, 'priitp')
    reservation_response = client.get('/reserve_book/1', follow_redirects=True)
    assert reservation_response.status_code == 200
    logout(client)
    login(client, 'toomask')
    response = client.get('/cancel_reservation/1', follow_redirects=True)
    assert response.status_code == 401


def test_cancel_reservation_own_book_not_reserved(client, first_user_with_books):
    login(client, 'juhanv')
    response = client.get('/cancel_reservation/1', follow_redirects=True)
    assert response.status_code == 404


def test_cancel_reservation_book_not_found(client, add_third_user):
    login(client, 'toomask')
    reservation_response = client.get('/reserve_book/1', follow_redirects=True)
    assert reservation_response.status_code == 404



