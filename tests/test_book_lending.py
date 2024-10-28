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
