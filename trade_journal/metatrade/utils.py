# accounts/utils.py
from cryptography.fernet import Fernet


# Generate a key for encryption (do this once and save it securely)
# You only need to create a key once; store it securely.
def generate_key():
    return Fernet.generate_key()


# Load your key from a secure location
# For demo purposes, let's assume this is your key:
# This should be securely stored and loaded in a real application
KEY = generate_key()  # This should be the byte string of the key


def encrypt_password(password: str) -> str:
    cipher = Fernet(KEY)
    """Encrypt the password."""
    encrypted_password = cipher.encrypt(password.encode())
    return encrypted_password.decode()  # Return as a string


def decrypt_password(encrypted_password: str, key_code: bytes) -> str:
    cipher = Fernet(key_code)
    """Decrypt the password."""
    decrypted_password = cipher.decrypt(encrypted_password.encode())
    return decrypted_password.decode()  # Return as a string
