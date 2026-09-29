import os

from fastapi import UploadFile

from shared.handlers.FilesHandler import FilesHandler


class CredentialsHandler:

    def __init__(self, base_path: str):
        self.base_path = base_path
        self.filesHandler = FilesHandler(base_path)

    async def write_credentials_json(self, credentials: UploadFile, user_id: str, storage_type: str) -> str:
        
        """Write Credentials file into a standard folder"""

        credentials_path = os.path.join(self.base_path, user_id, storage_type)

        if not self.filesHandler.check_dir(credentials_path): 
            os.makedirs(credentials_path)

        credentials_path = os.path.join(str(credentials_path), str(credentials.filename))

        await self.filesHandler.save(credentials_path, credentials.file)

        return str(credentials.filename)

    def is_valid(self, user_id: str, storage_type: str, credential_name: str) -> bool:
        """Check if a given credentials json exists"""

        path = os.path.join(self.base_path, user_id, storage_type)

        filename = os.path.join(path, credential_name)

        if self.filesHandler.check_dir(path) and self.filesHandler.check_file(filename):
            return True
        
        return False

    def list_user_credentials(self, user_id: str, storage_type: str) -> list[str]:

        path = os.path.join(self.base_path, user_id, storage_type)

        if not self.filesHandler.check_dir(path):
            return []

        all_entries = os.listdir(path)

        files = [entry for entry in all_entries if os.path.isfile(os.path.join(path, entry))]

        return files
    
    def get_credentials_path(self, user_id: str, storage_type: str, credential_name: str) -> str:
        """Check if a given credentials json exists"""

        return os.path.join(self.base_path, user_id, storage_type, credential_name)
