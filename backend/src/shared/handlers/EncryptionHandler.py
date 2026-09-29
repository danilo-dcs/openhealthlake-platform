import json
from cryptography.fernet import Fernet

from shared.models.env import EnvSettings
class EncryptionHandler:
    # FUNCTIONS

    def __init__(self) -> None:
        settings = EnvSettings()
        self.secret_key = str(settings.ENCRYPTION_SECRET_KEY)

    def generate_secret_key(self) -> str:
        """
        Generates a secret key for encryption and returns it as a string.
        """
        key = Fernet.generate_key()
        return key.decode()


    def load_secret_key(self, secret_key_str: str) -> bytes:
        """
        Converts the stored secret key string back to bytes.
        
        :param secret_key_str: The secret key as a string.
        :return: The secret key as bytes.
        """
        return secret_key_str.encode()


    def encrypt_credentials(self, credentials: dict) -> str:
        """
        Encrypts a dictionary of credentials using the provided secret key.
        
        :param credentials: The credentials dictionary to encrypt.
        :return: Encrypted credentials as a string.
        """
        fernet = Fernet(self.secret_key.encode())
        credentials_json = json.dumps(credentials)
        encrypted_credentials = fernet.encrypt(credentials_json.encode())
        return encrypted_credentials.decode()


    def decrypt_credentials(self, encrypted_credentials: str) -> dict:
        """
        Decrypts an encrypted credentials string using the provided secret key.
        
        :param encrypted_credentials: The encrypted credentials string.
        :return: The decrypted credentials as a dictionary.
        """
        fernet = Fernet(self.secret_key.encode())
        decrypted_credentials_json = fernet.decrypt(encrypted_credentials.encode())        
        return json.loads(decrypted_credentials_json.decode())