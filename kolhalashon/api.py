import os
import requests
from dotenv import load_dotenv
from typing import List, Dict
from .models.shiur import Shiur, ShiurDetails, Category, QualityLevel
from .models.exceptions import *
from .utils.session_manager import SessionManager

load_dotenv()

class KolHalashonAPI:
    def __init__(self, use_session=False, session_file='session.pkl'):
        self.username = os.getenv('KOL_HALASHON_USERNAME', '')
        self.password = os.getenv('KOL_HALASHON_PASSWORD', '')
        self.base_url = "https://srv.kolhalashon.com/api/"
        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'he-IL,he;q=0.9,en-AU;q=0.8,en;q=0.7,en-US;q=0.6',
            'authorization-site-key': 'Bearer 8ea2pe8',
            'content-type': 'application/json',
            'origin': 'https://www2.kolhalashon.com',
            'referer': 'https://www2.kolhalashon.com/',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        }
        
        self.use_session = use_session
        self.session_manager = SessionManager(session_file)
        
        if self.use_session:
            self._init_session()

    def _init_session(self):
        self.session_manager.load_session()
        if not self.session_manager.is_token_valid():
            self.login(self.username, self.password)

    def login(self, username: str, password: str):
        if not self.use_session:
            print("Session disabled, login not required.")
            return False
        
        login_url = f"{self.base_url}Accounts/UserLogin/"
        payload = {"Username": username, "Password": password}
        response = self.session_manager.session.post(login_url, json=payload, headers=self.headers)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('Token')
            if token:
                self.session_manager.set_token(token)
                return True
            raise AuthenticationError("Login successful but no token found.")
        raise AuthenticationError(f"Login failed with status code {response.status_code}")

    def search_items(self, keyword: str, user_id: int = -1) -> Category:
        url = f"{self.base_url}Search/WebSite_GetSearchItems/{keyword}/{user_id}/1/4"
        response = self.session_manager.session.get(url, headers=self.headers)
        if response.status_code == 200:
            return self.categorize_items(response.json())
        raise SearchFailedException(f"Error fetching data for keyword: {keyword}", response.status_code)

    def search_rav_shiurim(self, rav_id: int) -> List[Shiur]:
        """
        קבלת שיעורים של רב לפי ID באמצעות API העדכני של קול הלשון
        """
        # בדיקה אם ה-ID מגיע כמחרוזת ולא כמספר
        if isinstance(rav_id, str):
            try:
                rav_id = int(rav_id)
            except ValueError:
                raise SearchFailedException(f"Invalid Rav ID format: {rav_id}", 400)
        
        url = f"{self.base_url}Search/WebSite_GetRavShiurim/"
        
        # עדכון החיבור ל-Headers
        headers = self.headers.copy()
        if 'authorization-site-key' not in headers:
            # קוד ברירת מחדל - ייתכן שזה משתנה, צריך לבדוק אם יש דרך לקבל את זה דינמית
            headers['authorization-site-key'] = 'Bearer oxugrsl'  
        
        # מבנה הבקשה העדכני מבוסס על מה שראינו ב-curl
        data = {
            "QueryType": -1,
            "LangID": -1,
            "MasechetID": -1, 
            "DafNo": -1,
            "MasechetIDY": -1,
            "DafNoY": -1,
            "MoedID": -1,
            "ParashaID": -1,
            "EnglishDisplay": False,
            "MasechetIDYOz": -1,
            "DafNoYOz": -1,
            "FromRow": 0,
            "NumOfRows": 24,
            "PrefferedLanguage": -1,
            "SearchOrder": 7,
            "FiltersArray": [],
            "GeneralID": rav_id,
            "FilterSwitch": "1" * 95  # מספיק ארוך להכיל את כל הסינון
        }
        
        try:
            # שימוש בסשן הקיים לשליחת הבקשה
            response = self.session_manager.session.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                return self.format_shiurim(response.json())
            
            # אם נכשל, הצג מידע על השגיאה
            error_text = ""
            try:
                error_text = response.text[:200]
            except:
                pass
                
            raise SearchFailedException(f"Error fetching Rav Shiurim for Rav ID: {rav_id}. Response: {error_text}", response.status_code)
        except Exception as e:
            if not isinstance(e, SearchFailedException):
                raise SearchFailedException(f"Exception while fetching Rav Shiurim for Rav ID: {rav_id}. Error: {str(e)}", 500)
            else:
                raise e

    def download_file(self, file_id: int, quality_level: QualityLevel) -> str:
        if not self.use_session:
            raise SessionDisabledException()

        download_key = self.session_manager.get_download_key(file_id)
        url = f"{self.base_url}files/GetFileDownload/{file_id}/{quality_level.value}/{download_key}/null/false/false"
        
        file_extension = 'mp3' if quality_level == QualityLevel.AUDIO else 'mp4'
        quality_name = 'audio' if quality_level == QualityLevel.AUDIO else 'video' if quality_level == QualityLevel.VIDEO else 'hd'
        file_name = f"shiur_{file_id}_{quality_name}.{file_extension}"

        response = self.session_manager.session.get(url, headers=self.headers, stream=True)
        if response.status_code == 200:
            with open(file_name, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            return file_name
        raise DownloadFailedException("Download failed", response.status_code, file_id, quality_level)

    def get_shiur_details(self, file_id: int) -> ShiurDetails:
        url = f"{self.base_url}TblShiurimLists/WebSite_GetShiurDetails/{file_id}"
        response = self.session_manager.session.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return self._parse_shiur_details(response.json())
        raise ShiurDetailsNotFoundException(file_id)

    @staticmethod
    def categorize_items(items: List[Dict]) -> Category:
        categories = Category(rabanim=[], books=[], shiurim=[], others=[])
        for item in items:
            # יצירת עותק של הפריט עם המפתחות הנחוצים
            processed_item = item.copy()
            
            # הוספת המפתחות הסטנדרטיים שהקוד הקיים מחפש
            processed_item["ID"] = item.get("SearchItemId")
            processed_item["NameHebrew"] = item.get("SearchItemTextHebrew")
            
            search_item_type = item.get("SearchItemType")
            if search_item_type == 2:
                categories.rabanim.append(processed_item)
            elif search_item_type == 8:
                categories.books.append(processed_item)
            elif search_item_type == 10:
                categories.shiurim.append(processed_item)
            else:
                categories.others.append(item)
        return categories

    @staticmethod
    def format_shiurim(shiurim: List[Dict]) -> List[Shiur]:
        return [
            Shiur(
                file_id=shiur.get("FileId", 0),
                title=shiur.get("TitleHebrew", ""),
                rav=shiur.get("UserNameHebrew", ""),
                duration=shiur.get("ShiurDuration", "Unavailable"),
                record_date=shiur.get("RecordDate", ""),
                main_topic=shiur.get("MainTopicHebrew", ""),
                category_1=shiur.get("CatDesc1", ""),
                category_2=shiur.get("CatDesc2", ""),
                audio_available=shiur.get("HasAudio", False),
                video_available=shiur.get("HasVideo", False),
                hd_video_available=shiur.get("HasHdVideo", False),
                download_count=shiur.get("DownloadCount", 0),
                women_only=shiur.get("IsWomenOnly", False),
                shiur_type=shiur.get("ShiurType", "Unavailable"),
                viewed_by_user=shiur.get("ViewdByUser", False)
            ) for shiur in shiurim
        ]

    @staticmethod
    def _parse_shiur_details(data: Dict) -> ShiurDetails:
        return ShiurDetails(
            file_id=data.get("FileId", 0),
            title=data.get("TitleHebrew", ""),
            rav=data.get("UserNameHebrew", ""),
            duration=data.get("ShiurDuration", "Unavailable"),
            record_date=data.get("RecordDate", ""),
            main_topic=data.get("MainTopicHebrew", ""),
            audio_available=data.get("HasAudio", False),
            video_available=data.get("HasVideo", False),
            hd_video_available=data.get("HasHdVideo", False),
            categories=[data.get("CatDesc1", ""), data.get("CatDesc2", "")]
        )
        
    def get_all_rav_shiurim(self, rav_id: int) -> List[Shiur]:
        """
        קבלת כל השיעורים של רב מסוים בכל הדפים
        
        Args:
            rav_id (int): המזהה של הרב
            
        Returns:
            List[Shiur]: רשימה מלאה של כל השיעורים
        """
        all_shiurim = []
        batch_size = 24
        from_row = 0
        has_more = True
        
        while has_more:
            # בדיקה אם ה-ID מגיע כמחרוזת ולא כמספר
            if isinstance(rav_id, str):
                try:
                    rav_id = int(rav_id)
                except ValueError:
                    raise SearchFailedException(f"Invalid Rav ID format: {rav_id}", 400)
            
            url = f"{self.base_url}Search/WebSite_GetRavShiurim/"
            
            # מבנה הבקשה כולל את המיקום הנוכחי בתוצאות
            data = {
                "QueryType": -1,
                "LangID": -1,
                "MasechetID": -1, 
                "DafNo": -1,
                "MasechetIDY": -1,
                "DafNoY": -1,
                "MoedID": -1,
                "ParashaID": -1,
                "EnglishDisplay": False,
                "MasechetIDYOz": -1,
                "DafNoYOz": -1,
                "FromRow": from_row,  # מיקום התחלתי
                "NumOfRows": batch_size,  # כמה להביא בכל פעם
                "PrefferedLanguage": -1,
                "SearchOrder": 7,
                "FiltersArray": [],
                "GeneralID": rav_id,
                "FilterSwitch": "1" * 111
            }
            
            try:
                # שליחת הבקשה
                response = self.session_manager.session.post(url, headers=self.headers, json=data)
                
                if response.status_code == 200:
                    batch_shiurim = response.json()
                    formatted_shiurim = self.format_shiurim(batch_shiurim)
                    
                    # הוספת התוצאות לרשימה הכוללת
                    all_shiurim.extend(formatted_shiurim)
                    
                    # בדיקה אם יש עוד תוצאות
                    if len(batch_shiurim) < batch_size:
                        has_more = False  # אם קיבלנו פחות מהכמות המבוקשת, סיימנו
                    else:
                        from_row += batch_size  # עדכון המיקום לדף הבא
                        
                    print(f"נאספו עוד {len(formatted_shiurim)} שיעורים. סה\"כ: {len(all_shiurim)}")
                else:
                    # אם יש שגיאה, מפסיקים
                    error_text = ""
                    try:
                        error_text = response.text[:200]
                    except:
                        pass
                    
                    raise SearchFailedException(f"Error fetching Rav Shiurim batch for Rav ID: {rav_id}. Response: {error_text}", response.status_code)
            
            except Exception as e:
                if not isinstance(e, SearchFailedException):
                    raise SearchFailedException(f"Exception while fetching Rav Shiurim batch for Rav ID: {rav_id}. Error: {str(e)}", 500)
                else:
                    raise e
        
        return all_shiurim