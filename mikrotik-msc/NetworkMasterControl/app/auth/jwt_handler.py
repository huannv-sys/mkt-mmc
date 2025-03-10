import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your_secret_key"

def create_token(data):
    return jwt.encode({"exp": datetime.utcnow() + timedelta(hours=1), **data}, SECRET_KEY, algorithm="HS256")

def verify_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None

# Example usage
if __name__ == "__main__":
    token = create_token({"user_id": 1})
    print(token)
    print(verify_token(token))
