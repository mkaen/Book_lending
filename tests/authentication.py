
def login(client, username: str):
    """Log in the user."""
    try:
        response = client.post('/login', data={
            'username': username,
            'password': '123456'
        }, follow_redirects=True)
        return response
    except Exception as e:
        return e


def logout(client):
    """Log out the user."""
    response = client.get('/logout', follow_redirects=True)
    return response
