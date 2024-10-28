
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
