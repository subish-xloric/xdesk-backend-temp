import os
import boto3
from cryptography.fernet import Fernet
from django.conf import settings
from pTracker.common.logs import Logs
from pTracker.common.exception_handler import ExceptionHandler

class FileManager:
    """
    A centralized service to manage file uploads, reads, and deletions.
    Supports switching between LOCAL and S3 storage using settings.FILE_UPLOAD_MODE.
    """
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        
        # Initialize Fernet cipher for encryption/decryption
        try:
            self.cipher_suite = Fernet(settings.FERNET_KEY)
        except AttributeError:
            # Fallback if FERNET_KEY is missing in some environments
            self.cipher_suite = None
            
        self.mode = getattr(settings, 'FILE_UPLOAD_MODE', 'LOCAL')
        
        if self.mode == 'S3':
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
                region_name=getattr(settings, 'AWS_S3_REGION_NAME', None)
            )
            self.bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)

    def _get_s3_key(self, file_path):
        """
        Converts absolute local paths to relative S3 keys.
        Example: '/var/www/dm_ptracker/confidential_docs/file.pdf' -> 'confidential_docs/file.pdf'
        """
        if file_path.startswith('/var/www/dm_ptracker/'):
            return file_path.replace('/var/www/dm_ptracker/', '')
        if hasattr(settings, 'MEDIA_ROOT') and file_path.startswith(settings.MEDIA_ROOT):
            return file_path.replace(settings.MEDIA_ROOT, '')
            
        # Remove leading slash to make it a valid S3 key
        if file_path.startswith('/'):
            return file_path[1:]
        return file_path

    def upload_file(self, file_path, file_content):
        """
        Uploads raw file content to either LOCAL or S3.
        """
        try:
            if self.mode == "S3":
                s3_key = self._get_s3_key(file_path)
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=file_content
                )
            else:
                # Local Storage
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(file_content)
            return True
        except Exception as e:
            self.__log.error(f"Failed to upload file to {self.mode}: {str(e)} - {self.__exception.get_exception()}")
            return False

    def read_file(self, file_path):
        """
        Reads raw file content from either LOCAL or S3.
        """
        try:
            if self.mode == "S3":
                s3_key = self._get_s3_key(file_path)
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                return response['Body'].read()
            else:
                # Local Storage
                with open(file_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            self.__log.error(f"Failed to read file from {self.mode}: {str(e)} - {self.__exception.get_exception()}")
            return None

    def delete_file(self, file_path):
        """
        Deletes a file from either LOCAL or S3.
        """
        try:
            if self.mode == "S3":
                s3_key = self._get_s3_key(file_path)
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            else:
                # Local Storage
                if os.path.exists(file_path):
                    os.remove(file_path)
            return True
        except Exception as e:
            self.__log.error(f"Failed to delete file from {self.mode}: {str(e)} - {self.__exception.get_exception()}")
            return False

    def upload_encrypted_file(self, file_path, file_content):
        """
        Encrypts the file content using Fernet before uploading.
        """
        if not self.cipher_suite:
            raise ValueError("FERNET_KEY not configured in settings.")
            
        encrypted_content = self.cipher_suite.encrypt(file_content)
        return self.upload_file(file_path, encrypted_content)

    def read_encrypted_file(self, file_path):
        """
        Reads and decrypts the file content using Fernet.
        """
        if not self.cipher_suite:
            raise ValueError("FERNET_KEY not configured in settings.")
            
        encrypted_content = self.read_file(file_path)
        if encrypted_content:
            return self.cipher_suite.decrypt(encrypted_content)
        return None
