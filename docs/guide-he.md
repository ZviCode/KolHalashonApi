<div dir="rtl">

# מדריך בעברית

ספריית פייתון לעבודה מול האתר של [קול הלשון](https://www.kolhalashon.com/he/regularSite/home).

## התקנה

```bash
pip install kolhalashon
pip install "kolhalashon[dotenv]"   # לטעינת שם משתמש וסיסמה מקובץ .env
```

נדרש Python 3.10 ומעלה.

## מה אפשר לעשות בלי חשבון

```python
from kolhalashon import KolHalashonAPI, QualityLevel

api = KolHalashonAPI()

# חיפוש מהיר: רבנים, קטגוריות וכותרות
result = api.search_items("אשר וייס")
print(result.rabanim[0].id, result.rabanim[0].name)

# חיפוש מלא, חיפוש רבנים, רבנים פופולריים
shiurim = api.search_shiurim("הלכות שבת", limit=20)
ravs = api.search_ravs("וייס")

# השיעורים והתיקיות של רב
for shiur in api.iter_rav_shiurim(7, limit=50):
    print(shiur.file_id, shiur.title, shiur.duration)
folders = api.get_rav_folders(7)
shiurim = list(api.iter_folder_shiurim(folders[0].folder_id))

# פרטי שיעור, קישור להאזנה, קבצי PDF מצורפים
details = api.get_shiur_details(42863638)
print(api.get_play_url(42863638, QualityLevel.VIDEO))
print(details.audio_url)
for pdf in api.get_attachments(42863638):
    print(pdf.title, pdf.url)

# שידורים חיים
for live in api.get_live_shiurim():
    print(live.rav, live.stream_url)
```

## RSS

לכל תיקייה באתר יש פיד RSS (פודקאסט). הכפתור כבר לא מוצג באתר, אבל הפידים עדיין פעילים.

```python
url = api.get_rss_url(5761, rav_id=7)  # כתובת הפיד של תיקייה
url = api.get_shiur_rss_url(42863638)  # הפיד של התיקייה שהשיעור נמצא בה

feed = api.load_rss(5761, rav_id=7)  # טעינת הפיד
for item in feed:
    print(item.published, item.title, item.url)
```

כל עמוד בפיד מכיל עד 100 פריטים. `iter_rss` עובר על כל העמודים. פרטים נוספים ב[דף ה-RSS](rss.md).

## התחברות והורדה

ההורדה הרשמית דורשת חשבון. אפשר להעביר את הפרטים ישירות או לשים אותם בקובץ `.env`:

```
KOL_HALASHON_USERNAME=123456
KOL_HALASHON_PASSWORD=הסיסמה
```

```python
api = KolHalashonAPI.from_env()

api.download_file(42863638, QualityLevel.AUDIO, "downloads", use_server_filename=True)

# הורדת תיקייה שלמה או כל השיעורים של רב
api.download_folder(5761, "downloads/weiss", filename_template="{date} {title}")
api.download_rav(7, "downloads/rav-7", limit=100, with_attachments=True)
```

- קוד משתמש בן 6 ספרות מומר כמו בטופס ההתחברות של האתר (מתווספת 9 בהתחלה).
- הטוקן נשמר בקובץ `kolhalashon_session.json` ומשמש שוב עד שתוקפו פג.
- בהורדה מרובה קבצים קיימים מדולגים, כך שאפשר להמשיך הורדה שנקטעה. שגיאות נאספות ב-`DownloadResult.error` וההורדה ממשיכה.
- שדות לתבנית שם הקובץ: `{file_id}`, `{title}`, `{rav}`, `{rav_id}`, `{folder_id}`, `{date}`, `{quality}`.

## שורת פקודה

```bash
kolhalashon ravs "וייס"
kolhalashon folders 7
kolhalashon rss 5761 --rav 7 --load
kolhalashon live
kolhalashon --env download-folder 5761 -o downloads -t "{date} {title}"
```

כל הפקודות ב[דף שורת הפקודה](cli.md).

## Cloudflare

ה-API של האתר מוגן ע"י Cloudflare. הספרייה משתמשת ב-cloudscraper כדי לעבור את הבדיקה. אם בכל זאת
הבקשה נחסמת, נזרקת השגיאה `CloudflareChallengeError`.

## תקלות

אם משהו מפסיק לעבוד כי האתר השתנה, אפשר לפתוח
[issue](https://github.com/ZviCode/KolHalashonApi/issues/new). תיאור ה-endpoints שהספרייה משתמשת
בהם נמצא ב[הערות על ה-API של האתר](site-api.md).

</div>
