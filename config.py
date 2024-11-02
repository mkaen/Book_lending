class TestConfig:
    """Test configuration for Flask."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    LOGIN_DISABLED = False
    SESSION_PROTECTION = None
