import pickle
import os
import logging
import requests
from ..models.exceptions import SessionNotLoadedException, DownloadKeyNotFoundException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, session_file='session.pkl'):
        self.session_file = session_file
        self.session = requests.Session()
        self.auth_token = None
        self.headers = {}
        
    def load_session(self):
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'rb') as file:
                    session_data = pickle.load(file)
                    self.session.cookies.update(session_data.get('cookies', {}))
                    self.auth_token = session_data.get('auth_token')
                    self.headers = session_data.get('headers', {})
                    if self.auth_token:
                        self.headers['authorization'] = f'Bearer {self.auth_token}'
                    logger.info("Session loaded successfully")
            except Exception as e:
                raise SessionNotLoadedException() from e
        else:
            raise SessionNotLoadedException()
            
    def save_session(self):
        session_data = {
            'cookies': self.session.cookies.get_dict(),
            'auth_token': self.auth_token,
            'headers': self.headers
        }
        with open(self.session_file, 'wb') as file:
            pickle.dump(session_data, file)
        logger.info("Session saved successfully")

    def is_token_valid(self) -> bool:
        if not self.auth_token:
            return False
        
        test_file_id = 30413171
        try:
            self.get_download_key(test_file_id)
            return True
        except:
            return False

    def set_token(self, token: str):
        self.auth_token = token
        self.headers['authorization'] = f'Bearer {token}'
        self.save_session()
        
    def get_download_key(self, file_id: int) -> str:
        url = "https://www2.kolhalashon.com:444/api/files/checkAutorizationDownload/{}/false".format(file_id)
        response = self.session.get(url, headers=self.headers)
        
        if response.status_code == 200:
            key = response.json().get('key')
            if key:
                logger.debug(f"Download key retrieved successfully: {key}")
                return key
        raise DownloadKeyNotFoundException(file_id)