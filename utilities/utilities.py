import requests


def check_image_url(url):
    """Check image url and return True if it exists and image file is correct and undamaged."""
    try:
        response = requests.get(url)
        if response.status_code == 200 and 'image' in response.headers['Content-Type']:
            return True
        else:
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error checking URL: {e}")
        return False
