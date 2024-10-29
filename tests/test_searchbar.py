from setup_users_and_books import client, first_user_with_books, second_user_with_books


def test_search_books_by_author(client, first_user_with_books, second_user_with_books):
    response = client.get('/searchbar/?query=kiyosaki', follow_redirects=True)
    assert response.status_code == 200
    assert b"Rich Dad Poor Dad" in response.data
    assert b"Before You Quit Your Job" in response.data
    assert b"Harry Potter and the Sorcerer's Stone" not in response.data
    assert b"Harry Potter and the Chamber of Secrets" not in response.data


def test_search_books_by_title(client, first_user_with_books, second_user_with_books):
    response = client.get('/searchbar/?query=potter', follow_redirects=True)
    assert response.status_code == 200
    assert b"Harry Potter and the Sorcerer's Stone" in response.data
    assert b"Harry Potter and the Chamber of Secrets" in response.data
    assert b"Rich Dad Poor Dad" not in response.data
    assert b"Before You Quit Your Job" not in response.data


def test_search_books_blank_input(client, first_user_with_books, second_user_with_books):
    response = client.get('/searchbar/?query= ', follow_redirects=True)
    assert response.status_code == 200
    assert b"Wrong input" in response.data
    assert b"Harry Potter and the Sorcerer's Stone" not in response.data
    assert b"Harry Potter and the Chamber of Secrets" not in response.data
    assert b"Rich Dad Poor Dad" not in response.data
    assert b"Before You Quit Your Job" not in response.data
