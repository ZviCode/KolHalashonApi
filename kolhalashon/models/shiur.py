from dataclasses import dataclass
from typing import List, Dict
from enum import Enum

class QualityLevel(Enum):
    AUDIO = 1
    VIDEO = 2
    HD_VIDEO = 3

@dataclass
class Shiur:
    file_id: int
    title: str
    rav: str
    duration: str
    record_date: str
    main_topic: str
    category_1: str
    category_2: str
    audio_available: bool
    video_available: bool
    hd_video_available: bool
    download_count: int
    women_only: bool
    shiur_type: str
    viewed_by_user: bool

@dataclass
class ShiurDetails:
    file_id: int
    title: str
    rav: str
    duration: str
    record_date: str
    main_topic: str
    audio_available: bool
    video_available: bool
    hd_video_available: bool
    categories: List[str]

@dataclass
class Category:
    rabanim: List[Dict]
    books: List[Dict]
    shiurim: List[Dict]
    others: List[Dict]