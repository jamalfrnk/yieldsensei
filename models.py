from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id=None, username=None, email=None):
        self.id = id
        self.username = username
        self.email = email
        
    @staticmethod
    def get(user_id):
        """
        This is a mock user getter since we don't have a database yet.
        In production, this would query the database.
        """
        # For development, return a mock user
        if user_id == 1:
            return User(id=1, username="dev_user", email="dev@example.com")
        return None
