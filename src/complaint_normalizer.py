"""
complaint_normalizer.py
───────────────────────
Yorum metinlerini embedding işleminden önce temizlemek ve normalleştirmek için
merkezi bir modül.

DÜZELTİLEN HATALAR & GÜNCELLEMELER:
  - normalize_complaint() tuple yerine str döndürüyordu (sondaki virgül sabitlendi).
  - Türkçe karakterler ASCII dönüşümünden ÖNCE küçük harfe çekilmeli.
  - _apply_typo_map ASCII sonrası çalışacak şekilde güncellendi.
  - YENİ: Apple dışı sektörlerin kurumsal şirket tanıtım metinlerini (Aras Kargo, UPS, Metro Turizm) 
    tespit edip temizleyen kurumsal filtre eklendi.
"""
import re
import unicodedata

# Türkçe yazım hataları, kısaltmalar ve varyasyonlar için harita.
_TYPO_MAP = {
    # Şarj varyasyonları
    "sarz": "sarj",
    # Telefon kısaltmaları
    "telofon": "telefon",
    "tlf": "telefon",
    # Fiil/sözcük hataları
    "kasıyo": "kasiyor",
    "donuyo": "donuyor",
    "takiliyo": "takiliyor",
    "takılıyo": "takiliyor",
    # Cihaz yazım hataları (ASCII formda)
    "applewatch": "apple watch",
    "airpod": "airpods",
    "macbookda": "macbook",
    "iphonda": "iphone",
    "iphone da": "iphone",
    # İngilizce-Türkçe karışımları (sorun kelimeleri)
    "screen": "ekran",
    "battery": "batarya",
    "update": "guncelleme",
    "performance": "performans",
    "camera": "kamera",
    "problem": "sorun",
}

# Şikayetvar veya kurumsal tanıtım sayfalarındaki reklam/tanıtım metinlerini yakalamak için anahtar kelimeler
_KURUMSAL_KIRLILIK_PATTERNS = [
    r"aras kargo, 1979 yilinda",
    r"yillardir sektorun lider isimlerinden biri olmayi basaran ups",
    r"nilufer turizm kara seyahatinde",
    r"tokat yildizi ulasim, 2001 yilindan beri",
    r"kamil koc otobusleri turkiye",
    r"metro turizm'in verdigi hizmetler",
    r"surat kargo'dan alabileceginiz",
    r"kolay gelsin kargo firmasinin odaginda",
    r"genis erisim agina sahip",
    r"tasimacilik kuruluslarindan",
    r"arac filosu ve \d+\.\d+ kisilik uzman kadrosu",
    r"sehirler arasi kara yolculuguyla",
    r"yolcu tasimaciligi",
    r"koltuk dizilimine sahip",
]

def _apply_typo_map(text: str) -> str:
    """Sözlükteki düzeltmeleri kelime/söz öbeği sınırlarıyla uygula."""
    for wrong, right in sorted(_TYPO_MAP.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = r"\b" + re.escape(wrong) + r"\b"
        text = re.sub(pattern, right, text)
    return text

def _kurumsal_reklam_mi(text: str) -> bool:
    """Metnin bir kullanıcı şikayeti değil, otomatik kurumsal tanıtım metni olup olmadığını kontrol eder."""
    # Metin zaten küçük harf ve ASCII formda olacağı için doğrudan regex eşleştirmesi yapabiliriz
    for pattern in _KURUMSAL_KIRLILIK_PATTERNS:
        if re.search(pattern, text):
            return True
    return False

def normalize_complaint(text: str) -> str:
    """
    Bir şikayet metnini işlenmeye hazır hale getirmek için temizler ve normalleştirir.
    Eğer kurumsal bir reklam/tanıtım metni tespit edilirse boş string döndürür.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    # 1. Türkçe karakterleri koru → küçük harfe çevir → NFKD normalize → ASCII
    t = text
    t = t.replace("İ", "i").replace("I", "i")
    t = t.lower()
    
    _TR_TO_ASCII = str.maketrans("ığşçöü", "igscou")
    t = t.translate(_TR_TO_ASCII)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")

    # [YENİ] 1.5 ADIM: Kurumsal kargo/turizm firmalarının sabit tanıtım metinlerini filtrele
    if _kurumsal_reklam_mi(t):
        return ""  # Bu veri kirli, direkt eliyoruz!

    # 2. URL, e-posta, uzun sayısal diziler temizle
    t = re.sub(r'http\S+|www\S+|https\S+', ' ', t)
    t = re.sub(r'\S+@\S+', ' ', t)
    t = re.sub(r'\b\d{7,}\b', ' ', t)

    # 3. Yazım hatası düzeltme
    t = _apply_typo_map(t)

    # 4. İzin verilen karakterler dışındakileri temizle
    t = re.sub(r'[^\w\s.,?!-]', ' ', t)

    # 5. "Devamını oku" gibi scraping artıkları
    t = re.sub(r'devamini oku', ' ', t, flags=re.IGNORECASE)

    # 6. Tekrarlayan karakterleri sınırla (örn. "çoooook" → "çook")
    t = re.sub(r'(\w)\1{3,}', r'\1\1', t)

    # 7. Fazla boşlukları temizle
    t = re.sub(r'\s+', ' ', t).strip()

    return t