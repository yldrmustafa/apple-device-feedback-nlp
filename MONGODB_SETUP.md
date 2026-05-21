# 🍎 Apple Feedback NLP - MongoDB Entegre Pipeline

## 📋 Modüler Yapı (Güncellenmiş)

Orijinal yapı korundu ve MongoDB entegrasyonu eklendi:

```
src/
├── yorum_cek.py              # 🔍 Şikayetvar scraper (yorum çekme)
├── yorum_kaydet.py           # 💾 MongoDB kaydı (MongoDB entegrasyonu)
├── yorum_kumeleme_v2.py      # 🧠 Kategorileme (SBERT + MongoDB)
├── cihaz_tespit.py           # 📱 Cihaz tanıma
├── cihaz_normalize.py        # 🏷️  Cihaz normalizasyonu
├── feedback_uret.py          # 📊 Feedback üretme
├── config.json               # ⚙️  URL listesi
└── ...
```

## 🚀 Hızlı Başlangıç

### 1. MongoDB'yi Başlat (Terminal 1)
```powershell
mongod --dbpath D:\mongo_data
```

### 2. Virtual Environment'ı Etkinleştir (Terminal 2)
```powershell
cd d:\Bitirme_Projesi\apple-device-feedback-nlp
.venv\Scripts\activate
```

### 3. Gerekli Paketleri Yükle
```powershell
pip install -r requirements.txt
```

### 4. Yorumları Çek ve Kaydet (Terminal 2)
```powershell
cd src
python yorum_cek.py
```

### 5. Yorumları Kategorilendirirlir (Terminal 2)
```powershell
python yorum_kumeleme_v2.py
```

---

## 📊 İş Akışı

```
1. yorum_cek.py
   ↓
   Şikayetvar'dan yorumları çeker
   ↓
   yorum_kaydet.py → MongoDB'ye kaydet
   ↓
2. yorum_kumeleme_v2.py
   ↓
   MongoDB'deki işlenmemiş yorumları okur
   ↓
   SBERT embedding'i + Cosine Similarity
   ↓
   Kategorilendirirlir ve database'i güncelle
```

---

## 🗄️ MongoDB Şeması

```javascript
{
  _id: ObjectId,
  source: "sikayetvar",              // Veri kaynağı
  comment: "Yorum metni",
  normalized_comment: "yorum metni", // Temizlenmiş ve normalleştirilmiş yorum
  comment_hash: "md5_hash",          // Duplicate kontrol
  device_name: "iphone-13",
  url: "https://...",
  scraped_at: ISODate,
  processed: false,                  // Kategorilendirme durumu
  category: "Batarya ve şarj sorunu", // Kategorisi
  processed_at: ISODate
}
```

## 📖 Modül Açıklamaları

### yorum_kaydet.py
MongoDB veritabanı işlemleri için merkezi yönetici

**Temel Sınıf:**
- `CommentSaver` - Yorumları MongoDB'ye kaydeder

**Ana Metodlar:**
- `kaydet(yorum, cihaz, source, url)` - Tekil yorum
- `kaydet_toplu(yorumlar, cihaz, source)` - Toplu yorum
- `kapat()` - Bağlantıyı kapat

### yorum_cek.py
Şikayetvar'dan yorumları çeken Selenium scraper

**Özellikler:**
- Tüm sayfaları otomatik çeker
- MongoDB'ye doğrudan kaydet
- Duplicate otomatik engellenir
- Detaylı progress gösterimi

### yorum_kumeleme_v2.py
SBERT embedding'i ile kategorileme

**Özellikler:**
- 14 predefined kategori
- Cosine similarity eşleştirmesi
- Database batch işlemi
- Kategori emoji'leri

**14 Kategori:**
- 🔋 Batarya ve şarj sorunu
- 📺 Ekran ve görünüm sorunu
- 📷 Kamera sorunu
- ⚙️  Yazılım ve güncelleme sorunu
- 🏥 Servis ve garanti sorunu
- ⚡ Performans ve hız sorunu
- 🔥 Isınma sorunu
- 🔊 Ses ve ses kaydı sorunu
- 📡 Ağ ve bağlantı sorunu
- 💾 Depolama sorunu
- ☁️  iCloud ve hesap sorunu
- 💧 Su ve nem hasarı
- 💰 Fiyat ve ücret şikayeti
- 📦 Kargo ve teslimat sorunu

---

## 🔧 Başka Kaynak Eklemek

Yeni kaynak (Twitter, Reddit vb) eklemek için:

1. Yeni bir dosya oluştur (örn: `twitter_cek.py`)
2. `yorum_kaydet.py`'deki `CommentSaver` sınıfını kullan
3. Yorumları MongoDB'ye kaydet:

```python
from yorum_kaydet import CommentSaver

saver = CommentSaver()
tweets = [...]  # Scraping
saver.kaydet_toplu(tweets, source='twitter', device_name='iPhone 15')
saver.kapat()
```

---

## 📊 Database Sorgulama

**MongoDB CLI'de:**
```javascript
// MongoDB bağlan
mongo

// Database'i seç
use apple_feedback_db

// Toplam yorum sayısı
db.comments.countDocuments()

// Şikayetvar yorumları
db.comments.countDocuments({source: "sikayetvar"})

// İşlenmemiş yorumlar
db.comments.countDocuments({processed: false})

// İşlenmiş yorumlar
db.comments.countDocuments({processed: true})

// Kategoriye göre istatistik
db.comments.aggregate([
  {$group: {_id: "$category", count: {$sum: 1}}},
  {$sort: {count: -1}}
])

// Cihaza göre istatistik
db.comments.aggregate([
  {$group: {_id: "$device_name", count: {$sum: 1}}},
  {$sort: {count: -1}}
])
```

---

## ⚠️ Önemli Notlar

1. **MongoDB Gerekli** - İlk olarak `mongod`'u başlat
2. **Scraping Süresi** - Tüm URL'ler ≈ 3-5 saat
3. **Kategorileme Süresi** - 1000 yorum ≈ 2-3 dakika
4. **Rate Limiting** - Sikayet vb siteler engelleyebilir
5. **Duplicate Kontrol** - Otomatik olup gerçek yorum sayısından az kaydedilir

---

## 🐛 Troubleshooting

**Hata: "MongoDB bağlanamadı"**
```powershell
# MongoDB'yi doğru veri klasörü ile başlat
mongod --dbpath D:\mongo_data
```

**Hata: "PyMongo modülü yok"**
```powershell
pip install pymongo
```

**Hata: "Sentence Transformers yok"**
```powershell
pip install sentence-transformers
```

**Hata: "Scraping timeout"**
- Config.json'dan test URL'leri ile dene
- Ağ hızını kontrol et

---

## 📈 Sonraki Adımlar

1. ✅ Tüm kaynaklardan yorumları çek
2. ✅ Kategorilendirme yap
3. ⏳ Sentiment analizi ekle
4. ⏳ Trendler ve istatistikler oluştur
5. ⏳ Dashboard (Streamlit) yap
