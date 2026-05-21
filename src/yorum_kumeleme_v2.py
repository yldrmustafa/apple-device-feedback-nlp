"""
yorum_kumeleme_v2.py
────────────────────
Sentence Transformers + Semantic Similarity Matching

DÜZELTİLEN HATALAR:
  - _keyword_category() içinde normalize_complaint() çağrısı tuple döndürüyordu
    (complaint_normalizer.py'deki hata düzeltildi, ama burada da savunmalı kullanım eklendi).
  - normalize_complaint() sonucunun str olduğu kontrol edilir; değilse orijinal metin kullanılır.
  - _compute_category_embeddings() tekrar çağrıldığında gereksiz yeniden hesaplama önlendi.
  - DatabaseCategorizer.kategorilendire() içinde normalize_complaint() sonucu güvenli alınıyor.
"""

from typing import Dict, List
import sys
import io
import unicodedata
import re
from collections import defaultdict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from pymongo import MongoClient
from datetime import datetime
from complaint_normalizer import normalize_complaint

try:
    from sentence_transformers import SentenceTransformer
    import os

    print("  ... Sentence Transformer modeli yükleniyor...")
    
    # Modelin adını değil, indirdiğiniz klasörün yolunu yazın
    model_yolu = r'D:\Bitirme_Projesi\apple-device-feedback-nlp\modelv2base' # <-- KENDİ KLASÖR ADINIZI YAZIN
    
    _EMBEDDER = SentenceTransformer(
        model_yolu,
        device='cpu'
    )
    print("  OK Embedding modeli basariyla yuklendi!")
    _USE_EMBEDDINGS = True
except Exception as e:
    print(f"  HATA Model yuklemede hata: {e}")
    _USE_EMBEDDINGS = False
    _EMBEDDER = None

_CATEGORY_EMBEDDINGS_CACHE: dict[str, np.ndarray] = {}
_CATEGORIES = [
    "Batarya ve Şarj Sorunu",
    "Ekran ve Görünüm Sorunu",
    "Kamera Sorunu",
    "Yazılım ve Güncelleme Sorunu",
    "Servis ve Garanti Sorunu",
    "Performans ve Hız Sorunu",
    "Isınma Sorunu",
    "Ses ve Ses Kaydı Sorunu",
    "Ağ ve Bağlantı Sorunu",
    "Depolama Sorunu",
    "iCloud ve Hesap Sorunu",
    "Su ve Nem Hasarı",
    "Fiyat ve Ücret Şikayeti",
    "Kargo ve Teslimat Sorunu",
]

_CATEGORY_DESCRIPTIONS = [
    "Batarya ve Şarj Sorunu: pil bitiyor, şarj olmuyor, batarya şişmiş, şarj kablosu çalışmıyor, hızlı bitiyor",
    "Ekran ve Görünüm Sorunu: ekran kırık, dokunmatik çalışmıyor, ekranda çizgi var, ekran titriyor, görüntü bozuk",
    "Kamera Sorunu: kamera açılmıyor, fotoğraf bulanık, arka kamera çalışmıyor, ön kamera bozuk, video kaydedilmiyor",
    "Yazılım ve Güncelleme Sorunu: güncelleme yapılmıyor, uygulama çöküyor, iOS hatası, sistem donuyor, yazılım bozuk",
    "Servis ve Garanti Sorunu: servis ilgilenmiyor, garanti kapsamıyor, teknik destek yok, onarım yapılmadı",
    "Performans ve Hız Sorunu: telefon yavaş, uygulama açılmıyor, takılıyor, donuyor, kasıyor, geç açılıyor",
    "Isınma Sorunu: telefon ısınıyor, aşırı ısınma, pil şişiyor nedeniyle ısınma, kullanırken yanıyor",
    "Ses ve Ses Kaydı Sorunu: hoparlör çalışmıyor, ses yok, mikrofon bozuk, kulaklık girişi çalışmıyor, ses titriyor",
    "Ağ ve Bağlantı Sorunu: wifi bağlanmıyor, bluetooth çalışmıyor, sinyal yok, 5G bağlantı sorunu, internet yok",
    "Depolama Sorunu: hafıza dolu, depolama alanı yok, dosyalar silinmiyor, bellek az, storage sorunu",
    "iCloud ve Hesap Sorunu: iCloud yedekleme olmuyor, Apple ID sorunu, şifre sıfırlanamıyor, hesap kilitlendi",
    "Su ve Nem Hasarı: suya düştü, yağmurda ıslandı, nem girdi, su geçirmezlik çalışmıyor, sıvı hasar",
    "Fiyat ve Ücret Şikayeti: çok pahalı, fiyat yüksek, ücret iade edilmiyor, haksız faturalama, fahiş fiyat",
    "Kargo ve Teslimat Sorunu: ürün gelmedi, kargo gecikti, yanlış ürün geldi, paket hasar gördü, teslimat yapılmadı",
]

_EMOJI_MAP = {
    "Batarya ve Şarj Sorunu":       "🔋",
    "Ekran ve Görünüm Sorunu":      "📺",
    "Kamera Sorunu":                "📷",
    "Yazılım ve Güncelleme Sorunu": "⚙️",
    "Servis ve Garanti Sorunu":     "🏥",
    "Performans ve Hız Sorunu":     "⚡",
    "Isınma Sorunu":                "🔥",
    "Ses ve Ses Kaydı Sorunu":      "🔊",
    "Ağ ve Bağlantı Sorunu":        "📡",
    "Depolama Sorunu":              "💾",
    "iCloud ve Hesap Sorunu":       "☁️",
    "Su ve Nem Hasarı":             "💧",
    "Fiyat ve Ücret Şikayeti":      "💰",
    "Kargo ve Teslimat Sorunu":     "📦",
}

_AIRPODS_CATEGORIES = [
    "Bağlantı ve Eşleşme Sorunu",
    "Ses ve Mikrofon Sorunu",
    "Şarj ve Kutu Sorunu",
    "ANC ve Gürültü Engelleme Sorunu",
    "Bul ve Konum Sorunu",
    "Servis ve Garanti Sorunu",
    "Fiyat ve Ücret Şikayeti",
    "Kargo ve Teslimat Sorunu",
    "Diğer",
]

_AIRPODS_CATEGORY_DESCRIPTIONS = [
    "Bağlantı ve Eşleşme Sorunu: bluetooth bağlantısı kopuyor, eşleşmiyor, cihaz bağlanmıyor, telefon görmüyor, bağlantı kesiliyor",
    "Ses ve Mikrofon Sorunu: ses boğuk, cızırtı var, mikrofon çalışmıyor, karşı taraf duymuyor, ses kalitesi kötü, parazit",
    "Şarj ve Kutu Sorunu: kulaklık şarj olmuyor, kutu şarj olmuyor, pil çabuk bitiyor, case sorunlu, kutu çalışmıyor",
    "ANC ve Gürültü Engelleme Sorunu: aktif gürültü engelleme çalışmıyor, şeffaf mod bozuk, dış ses alıyor, anc sorunlu",
    "Bul ve Konum Sorunu: bul uygulaması, kayıp kulaklık, konum görünmüyor, find my çalışmıyor, yer tespiti yok",
    "Servis ve Garanti Sorunu: servis ilgilenmiyor, garanti kapsamıyor, değişim yapılmıyor, onarım reddedildi",
    "Fiyat ve Ücret Şikayeti: pahalı, ücret iade edilmiyor, fiyat yüksek, fahiş fiyat, ödeme sorunu",
    "Kargo ve Teslimat Sorunu: ürün gelmedi, kargo gecikti, yanlış ürün geldi, paket hasar gördü, teslimat yapılmadı",
    "Diğer: yukarıdaki sorunlardan hiçbirine girmeyen şikayetler",
]

_AIRPODS_EMOJI_MAP = {
    "Bağlantı ve Eşleşme Sorunu": "📡",
    "Ses ve Mikrofon Sorunu": "🔊",
    "Şarj ve Kutu Sorunu": "🔋",
    "ANC ve Gürültü Engelleme Sorunu": "🎧",
    "Bul ve Konum Sorunu": "📍",
    "Servis ve Garanti Sorunu": "🏥",
    "Fiyat ve Ücret Şikayeti": "💰",
    "Kargo ve Teslimat Sorunu": "📦",
    "Diğer": "📌",
}

_PHONE_CATEGORY_DESCRIPTIONS = _CATEGORY_DESCRIPTIONS
_PHONE_EMOJI_MAP = _EMOJI_MAP

_IPAD_CATEGORY_DESCRIPTIONS = [
    "Batarya ve Şarj Sorunu: iPad pil bitiyor, şarj olmuyor, Apple Pencil şarj olmuyor, batarya hızlı düşüyor",
    "Ekran ve Görünüm Sorunu: iPad ekran kırık, dokunmatik çalışmıyor, ekranda çizgi var, görüntü bozuk",
    "Kamera Sorunu: iPad kamera açılmıyor, fotoğraf bulanık, ön kamera bozuk, video kaydedilmiyor",
    "Yazılım ve Güncelleme Sorunu: iPadOS güncellemesi yapılmıyor, uygulama çöküyor, sistem donuyor, yazılım bozuk",
    "Servis ve Garanti Sorunu: servis ilgilenmiyor, garanti kapsamıyor, teknik destek yok, onarım yapılmadı",
    "Performans ve Hız Sorunu: iPad yavaş, uygulama açılmıyor, takılıyor, donuyor, kasıyor, geç açılıyor",
    "Isınma Sorunu: iPad ısınıyor, aşırı ısınma, kullanırken yanıyor, şarjdayken ısınıyor",
    "Ses ve Ses Kaydı Sorunu: hoparlör çalışmıyor, ses yok, mikrofon bozuk, kulaklık girişi çalışmıyor",
    "Ağ ve Bağlantı Sorunu: wifi bağlanmıyor, bluetooth çalışmıyor, sinyal yok, internet yok, hotspot sorunlu",
    "Depolama Sorunu: hafıza dolu, depolama alanı yok, dosyalar silinmiyor, bellek az, storage sorunu",
    "iCloud ve Hesap Sorunu: iCloud yedekleme olmuyor, Apple ID sorunu, şifre sıfırlanamıyor, hesap kilitlendi",
    "Su ve Nem Hasarı: suya düştü, yağmurda ıslandı, nem girdi, sıvı hasar",
    "Fiyat ve Ücret Şikayeti: çok pahalı, fiyat yüksek, ücret iade edilmiyor, haksız faturalama, fahiş fiyat",
    "Kargo ve Teslimat Sorunu: ürün gelmedi, kargo gecikti, yanlış ürün geldi, paket hasar gördü, teslimat yapılmadı",
]

_MAC_CATEGORY_DESCRIPTIONS = [
    "Batarya ve Şarj Sorunu: MacBook pil bitiyor, şarj olmuyor, adaptör çalışmıyor, batarya hızlı düşüyor",
    "Ekran ve Görünüm Sorunu: Mac ekran kırık, görüntü bozuk, ekranda çizgi var, panel titriyor",
    "Kamera Sorunu: kamera açılmıyor, görüntü bulanık, FaceTime kamerası bozuk, video kaydedilmiyor",
    "Yazılım ve Güncelleme Sorunu: macOS güncellemesi yapılmıyor, uygulama çöküyor, sistem donuyor, yazılım bozuk",
    "Servis ve Garanti Sorunu: servis ilgilenmiyor, garanti kapsamıyor, teknik destek yok, onarım yapılmadı",
    "Performans ve Hız Sorunu: Mac yavaş, uygulama açılmıyor, takılıyor, donuyor, fan sesi artıyor",
    "Isınma Sorunu: Mac ısınıyor, aşırı ısınma, fan çok çalışıyor, kullanırken yanıyor",
    "Ses ve Ses Kaydı Sorunu: hoparlör çalışmıyor, ses yok, mikrofon bozuk, kulaklık girişi çalışmıyor",
    "Ağ ve Bağlantı Sorunu: wifi bağlanmıyor, bluetooth çalışmıyor, sinyal yok, internet yok, hotspot sorunlu",
    "Depolama Sorunu: hafıza dolu, depolama alanı yok, disk dolu, dosyalar silinmiyor, storage sorunu",
    "iCloud ve Hesap Sorunu: iCloud yedekleme olmuyor, Apple ID sorunu, şifre sıfırlanamıyor, hesap kilitlendi",
    "Su ve Nem Hasarı: suya düştü, yağmurda ıslandı, nem girdi, sıvı hasar",
    "Fiyat ve Ücret Şikayeti: çok pahalı, fiyat yüksek, ücret iade edilmiyor, haksız faturalama, fahiş fiyat",
    "Kargo ve Teslimat Sorunu: ürün gelmedi, kargo gecikti, yanlış ürün geldi, paket hasar gördü, teslimat yapılmadı",
]

_WATCH_CATEGORIES = [
    "Batarya ve Şarj Sorunu",
    "Ekran ve Görünüm Sorunu",
    "Sensör ve Sağlık Sorunu",
    "Bağlantı ve Eşleşme Sorunu",
    "Yazılım ve Güncelleme Sorunu",
    "Performans ve Hız Sorunu",
    "Su ve Dayanıklılık Sorunu",
    "Kordon ve Donanım Sorunu",
    "Servis ve Garanti Sorunu",
    "Fiyat ve Ücret Şikayeti",
    "Kargo ve Teslimat Sorunu",
    "Diğer",
]

_WATCH_CATEGORY_DESCRIPTIONS = [
    "Batarya ve Şarj Sorunu: Apple Watch şarj olmuyor, pil hızlı bitiyor, kablosuz şarj problemi, kutu şarjı çalışmıyor",
    "Ekran ve Görünüm Sorunu: saat ekranı kırık, ekranda çizgi var, dokunmatik çalışmıyor, görüntü bozuk",
    "Sensör ve Sağlık Sorunu: kalp sensörü çalışmıyor, nabız ölçmüyor, aktivite halkaları hatalı, sağlık verisi yanlış",
    "Bağlantı ve Eşleşme Sorunu: saat telefona bağlanmıyor, bluetooth kopuyor, eşleşme sorunu, hücresel bağlantı yok",
    "Yazılım ve Güncelleme Sorunu: watchOS güncellemesi yapılmıyor, uygulama çöküyor, sistem donuyor, yazılım bozuk",
    "Performans ve Hız Sorunu: saat yavaş, menüler açılmıyor, takılıyor, donuyor, kasıyor",
    "Su ve Dayanıklılık Sorunu: suya dayanıklılık sorunu, ıslandı, havuzda bozuldu, su aldı, yağmurda problem",
    "Kordon ve Donanım Sorunu: kordon kopuyor, kasa çizildi, dijital crown bozuk, tuş çalışmıyor",
    "Servis ve Garanti Sorunu: servis ilgilenmiyor, garanti kapsamıyor, teknik destek yok, onarım yapılmadı",
    "Fiyat ve Ücret Şikayeti: çok pahalı, fiyat yüksek, ücret iade edilmiyor, haksız faturalama, fahiş fiyat",
    "Kargo ve Teslimat Sorunu: ürün gelmedi, kargo gecikti, yanlış ürün geldi, paket hasar gördü, teslimat yapılmadı",
    "Diğer: yukarıdaki sorunlardan hiçbirine girmeyen şikayetler",
]

_WATCH_EMOJI_MAP = {
    "Batarya ve Şarj Sorunu": "🔋",
    "Ekran ve Görünüm Sorunu": "📺",
    "Sensör ve Sağlık Sorunu": "❤️",
    "Bağlantı ve Eşleşme Sorunu": "📡",
    "Yazılım ve Güncelleme Sorunu": "⚙️",
    "Performans ve Hız Sorunu": "⚡",
    "Su ve Dayanıklılık Sorunu": "💧",
    "Kordon ve Donanım Sorunu": "⌚",
    "Servis ve Garanti Sorunu": "🏥",
    "Fiyat ve Ücret Şikayeti": "💰",
    "Kargo ve Teslimat Sorunu": "📦",
    "Diğer": "📌",
}

_MEDIA_CATEGORIES = [
    "Ses ve Kalite Sorunu",
    "Bağlantı ve Kurulum Sorunu",
    "Yazılım ve Güncelleme Sorunu",
    "Performans ve Hız Sorunu",
    "Servis ve Garanti Sorunu",
    "Fiyat ve Ücret Şikayeti",
    "Kargo ve Teslimat Sorunu",
    "Diğer",
]

_MEDIA_CATEGORY_DESCRIPTIONS = [
    "Ses ve Kalite Sorunu: ses bozuk, ses kalitesi kötü, cızırtı var, hoparlör bozuk, ses düşük",
    "Bağlantı ve Kurulum Sorunu: wifi bağlanmıyor, bluetooth çalışmıyor, kurulum tamamlanmıyor, cihaz eşleşmiyor",
    "Yazılım ve Güncelleme Sorunu: yazılım bozuk, güncelleme yapılmıyor, uygulama çöküyor, sistem donuyor",
    "Performans ve Hız Sorunu: cihaz yavaş, takılıyor, donuyor, geç açılıyor, komutlara geç tepki veriyor",
    "Servis ve Garanti Sorunu: servis ilgilenmiyor, garanti kapsamıyor, teknik destek yok, onarım yapılmadı",
    "Fiyat ve Ücret Şikayeti: çok pahalı, fiyat yüksek, ücret iade edilmiyor, haksız faturalama, fahiş fiyat",
    "Kargo ve Teslimat Sorunu: ürün gelmedi, kargo gecikti, yanlış ürün geldi, paket hasar gördü, teslimat yapılmadı",
    "Diğer: yukarıdaki sorunlardan hiçbirine girmeyen şikayetler",
]

_MEDIA_EMOJI_MAP = {
    "Ses ve Kalite Sorunu": "🔊",
    "Bağlantı ve Kurulum Sorunu": "📡",
    "Yazılım ve Güncelleme Sorunu": "⚙️",
    "Performans ve Hız Sorunu": "⚡",
    "Servis ve Garanti Sorunu": "🏥",
    "Fiyat ve Ücret Şikayeti": "💰",
    "Kargo ve Teslimat Sorunu": "📦",
    "Diğer": "📌",
}

_UNKNOWN_CATEGORIES = [
    "Platform ve Dolandırıcılık Sorunu",
    "Ödeme ve Ücret Sorunu",
    "Sipariş ve Teslimat Sorunu",
    "İletişim ve Destek Sorunu",
    "Hesap ve Güvenlik Sorunu",
    "Diğer",
]

_UNKNOWN_CATEGORY_DESCRIPTIONS = [
    "Platform ve Dolandırıcılık Sorunu: sahibinden, dolap, letgo, param guvende, guvenli odeme, sahte link, dolandiricilik, ilan, whatsapp uzerinden kandirma",
    "Ödeme ve Ücret Sorunu: para hesabima yatmadi, fazla ucret kesildi, komisyon, havale, kart cekimi, iade edilmedi, odeme gecikmesi",
    "Sipariş ve Teslimat Sorunu: siparis iptal edildi, urun gelmedi, kargo gecikti, teslimat yapilmadi, paket kayboldu, urun yollanmadi",
    "İletişim ve Destek Sorunu: musteri hizmetleri, destek, yanit verilmedi, arama, mesaj, geri donus, iletisim kurulamadı",
    "Hesap ve Güvenlik Sorunu: hesap kapatildi, guvenlik, sifre, dogrulama, giris yapamiyorum, yetkisiz erisim, hesap askıya alindi",
    "Diğer: yukarıdaki platform sorunlarından hiçbirine girmeyen şikayetler",
]

_UNKNOWN_EMOJI_MAP = {
    "Platform ve Dolandırıcılık Sorunu": "🧾",
    "Ödeme ve Ücret Sorunu": "💳",
    "Sipariş ve Teslimat Sorunu": "📦",
    "İletişim ve Destek Sorunu": "💬",
    "Hesap ve Güvenlik Sorunu": "🔐",
    "Diğer": "📌",
}

_CATEGORY_EMBEDDINGS = None
_CATEGORY_EMBEDDINGS_COMPUTED = False

_KEYWORD_RULES = [
    (r"\b(batarya|pil|sarj|sarz|charger|battery)\b|hizli bit",  "Batarya ve Şarj Sorunu"),
    (r"ekran|dokunmatik|display|lcd|oled|catlak|kirik|cizgi|titriyor|touch",
                                                                  "Ekran ve Görünüm Sorunu"),
    (r"kamera|fotograf|video|lens|odak|blur|bulanik|cekim|selfie|arka kamera|on kamera",
                                                                  "Kamera Sorunu"),
    (r"guncelleme|update|ios|yazilim|uygulama|app|cokuyor|crash|boot|sistem hatasi|format|yeniden kur",
                                                                  "Yazılım ve Güncelleme Sorunu"),
    (r"servis|garanti|teknik destek|yetkili|onarim|tamir|apple store|musteri hizmet",
                                                                  "Servis ve Garanti Sorunu"),
    (r"yavas|kasiyor|donuyor|takiliyor|performans|hiz|acilmiyor|gec ac|lag|fps",
                                                                  "Performans ve Hız Sorunu"),
    (r"isin|sicak|yaniyor|overhe|termal|ates gibi",              "Isınma Sorunu"),
    (r"ses\b|hoparlor|mikrofon|kulaklik|zil|audio|speaker|sound|duyulmuyor|ses yok|gurultu",
                                                                  "Ses ve Ses Kaydı Sorunu"),
    (r"wifi|wi-fi|bluetooth|sinyal|internet\b|baglanti|network|5g|4g|lte|hotspot|nfc|gsm|hat\b",
                                                                  "Ağ ve Bağlantı Sorunu"),
    (r"depolama|storage|hafiza|doldu|yer yok|gb\b|yedekleme alani|dosya sil",
                                                                  "Depolama Sorunu"),
    (r"icloud|apple id|hesap|sifre|senkronizasyon|sync|backup|yedek|oturum",
                                                                  "iCloud ve Hesap Sorunu"),
    (r"suya dus|islandi|nem|su\s*hasar|su\s*gecirmez|yagmur|sivi", "Su ve Nem Hasarı"),
    (r"fiyat|pahali|ucret|para|indirim|iade|fatura|fahis|odeme",  "Fiyat ve Ücret Şikayeti"),
    (r"kargo|teslimat|gelmedi|gecikti|yanlis urun|paket|kutu|kurye|siparis",
                                                                  "Kargo ve Teslimat Sorunu"),
]

_AIRPODS_KEYWORD_RULES = [
    (r"bluetooth|baglanti|baglanm|esles|pair|connect|kopuyor|kopma|gormuyor|telefon", "Bağlantı ve Eşleşme Sorunu"),
    (r"ses|mikrofon|boguk|cizirti|parazit|gurultu|duyulmuyor|karsi taraf|karşı taraf", "Ses ve Mikrofon Sorunu"),
    (r"sarj|sarz|batarya|pil|case|kutu.*sarj|sarj.*kutu|sarj olmuyor|şarj olmuyor|charging", "Şarj ve Kutu Sorunu"),
    (r"anc|aktif gürültü|aktif gurultu|gürültü engelleme|gurultu engelleme|seffaf mod|şeffaf mod|dis ses|dış ses", "ANC ve Gürültü Engelleme Sorunu"),
    (r"\bbul\b|find my|konum|kayip|kayıp|kaybol|locat", "Bul ve Konum Sorunu"),
    (r"servis|garanti|onarim|tamir|degisim|değişim|yetkili|apple store|musteri hizmet", "Servis ve Garanti Sorunu"),
    (r"fiyat|pahali|pahalı|ucret|ücret|para|indirim|iade|fatura|fahis|fahiş|odeme|ödeme", "Fiyat ve Ücret Şikayeti"),
    (r"kargo|teslimat|gelmedi|gecikti|yanlis urun|paket|kurye|siparis", "Kargo ve Teslimat Sorunu"),
]

_PLATFORM_SIGNAL_PATTERNS = [
    r"sahibinden",
    r"dolap",
    r"letgo",
    r"trendyol",
    r"hepsiburada",
    r"amazon",
    r"n11",
    r"param\s*guvende",
    r"guvenli\s*odeme",
    r"s[-\s]*param",
    r"whatsapp",
    r"\biban\b",
    r"\bilan\b",
    r"\bteklif\b",
    r"\bsatici\b",
    r"\balici\b",
    r"havale",
    r"kapora",
    r"dolandir",
    r"sahte\s*link",
    r"islem\s*ucreti",
    r"guvenlik\s*zafiyeti",
    r"musteri\s*hizmet",
]

_DEVICE_ISSUE_SIGNAL_PATTERNS = [
    r"ekran",
    r"dokunmatik",
    r"batarya",
    r"pil",
    r"sarj",
    r"sarz",
    r"kamera",
    r"yazilim",
    r"guncelleme",
    r"ios",
    r"watchos",
    r"macos",
    r"ses",
    r"mikrofon",
    r"hoparlor",
    r"wifi",
    r"bluetooth",
    r"baglanti",
    r"performans",
    r"yavas",
    r"donuyor",
    r"takiliyor",
    r"isin",
    r"sicak",
    r"icloud",
    r"apple id",
    r"servis",
    r"garanti",
    r"depolama",
    r"suya dus",
    r"islandi",
    r"nem",
]


def _safe_normalize(text: str) -> str:
    """
    normalize_complaint() sonucunun str olduğunu garanti eder.
    Eski hatalı kodda tuple dönebiliyordu — bu wrapper bunu yakalar.
    """
    result = normalize_complaint(text)
    if isinstance(result, tuple):
        # Güvenlik önlemi: tuple gelirse ilk elemanı al
        result = result[0] if result else ""
    return result if isinstance(result, str) else str(result)


def _keyword_category(text: str, rules: list[tuple[str, str]]) -> str | None:
    # DÜZELTME: _safe_normalize kullan; orijinalde doğrudan normalize_complaint()
    # çağrılıyordu ve tuple dönüşü downstream regex'i kırıyordu.
    normalized = _safe_normalize(text)
    normalized = (
        unicodedata.normalize("NFKD", normalized)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    for pattern, category in rules:
        if re.search(pattern, normalized):
            return category
    return None


def _label_text(category_name: str, emoji_map: dict[str, str]) -> str:
    return f"{emoji_map.get(category_name, '📌')} {category_name}"


def _resolve_category_with_priority(
    comment: str,
    model_category: str,
    model_score: float,
    semantic_threshold: float,
    keyword_rules: list[tuple[str, str]],
) -> tuple[str, str, str | None]:
    """Model öncelikli seçim yap; model zayıfsa keyword rule fallback uygula."""
    rule_category = _keyword_category(comment, keyword_rules)
    if model_score >= semantic_threshold and model_category != "Diğer":
        return model_category, "model", rule_category
    if rule_category:
        return rule_category, "kural", rule_category
    return model_category, "model", rule_category


def konu_disi_mi(text: str) -> bool:
    """Metin cihaz sorunu değil, platform/dolandırıcılık odaklı mı?"""
    normalized = _safe_normalize(text)
    normalized = (
        unicodedata.normalize("NFKD", normalized)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    has_platform_signal = any(re.search(pattern, normalized) for pattern in _PLATFORM_SIGNAL_PATTERNS)
    has_device_issue_signal = any(re.search(pattern, normalized) for pattern in _DEVICE_ISSUE_SIGNAL_PATTERNS)
    return has_platform_signal and not has_device_issue_signal


def _get_taxonomy(device_name: str | None):
    name = (device_name or "").lower()
    if name in {"bilinmeyen", "unknown", "genel", "other"}:
        return "unknown", _UNKNOWN_CATEGORIES, _UNKNOWN_CATEGORY_DESCRIPTIONS, _KEYWORD_RULES, _UNKNOWN_EMOJI_MAP
    if "airpods" in name:
        return "airpods", _AIRPODS_CATEGORIES, _AIRPODS_CATEGORY_DESCRIPTIONS, _AIRPODS_KEYWORD_RULES, _AIRPODS_EMOJI_MAP
    if "watch" in name:
        return "watch", _WATCH_CATEGORIES, _WATCH_CATEGORY_DESCRIPTIONS, _KEYWORD_RULES, _WATCH_EMOJI_MAP
    if "ipad" in name:
        return "ipad", _CATEGORIES, _IPAD_CATEGORY_DESCRIPTIONS, _KEYWORD_RULES, _PHONE_EMOJI_MAP
    if "mac" in name:
        return "mac", _CATEGORIES, _MAC_CATEGORY_DESCRIPTIONS, _KEYWORD_RULES, _PHONE_EMOJI_MAP
    if "homepod" in name or "apple tv" in name or "appletv" in name:
        return "media", _MEDIA_CATEGORIES, _MEDIA_CATEGORY_DESCRIPTIONS, _KEYWORD_RULES, _MEDIA_EMOJI_MAP
    return "iphone", _CATEGORIES, _PHONE_CATEGORY_DESCRIPTIONS, _KEYWORD_RULES, _PHONE_EMOJI_MAP


def _compute_category_embeddings(taxonomy_key: str, descriptions: list[str]):
    if taxonomy_key in _CATEGORY_EMBEDDINGS_CACHE or not _USE_EMBEDDINGS:
        return
    print("  ⏳ Kategori vektörleri hazırlanıyor...")
    _CATEGORY_EMBEDDINGS_CACHE[taxonomy_key] = _EMBEDDER.encode(descriptions, convert_to_numpy=True)
    print("  ✓ Kategori vektörleri hazır!")


def yorumlari_kumele(yorumlar: List[str], cihaz_adi: str | None = None) -> Dict[str, Dict]:
    """
    Yorumları kategorilere göre kümele.

    Returns:
        {
          "🔋 Batarya ve Şarj Sorunu": {
              "yorumlar": ["yorum1", "yorum2"],   # düz string listesi
              "sorun_sayısı": 2,
              "ort_skor": 0.85
          },
          ...
        }
    """
    if not yorumlar or not _USE_EMBEDDINGS:
        return {"📌 Genel": {"yorumlar": yorumlar, "sorun_sayısı": len(yorumlar), "ort_skor": 0.0}}

    taxonomy_key, categories, category_descriptions, keyword_rules, emoji_map = _get_taxonomy(cihaz_adi)
    _compute_category_embeddings(taxonomy_key, category_descriptions)

    categorized: dict = defaultdict(list)

    print(f"     ✓ {len(yorumlar)} yorum embedding'e dönüştürülüyor...")
    comment_embeddings = _EMBEDDER.encode(
        yorumlar, convert_to_numpy=True, show_progress_bar=False
    )

    print(f"     ✓ Kategori eşleştirmesi yapılıyor...")
    similarities = cosine_similarity(comment_embeddings, _CATEGORY_EMBEDDINGS_CACHE[taxonomy_key])
    best_indices = np.argmax(similarities, axis=1)
    best_scores  = np.max(similarities, axis=1)

    if taxonomy_key == "unknown":
        semantic_threshold = 0.30
    else:
        semantic_threshold = 0.32 if taxonomy_key == "airpods" else 0.35

    for comment, cat_idx, score in zip(yorumlar, best_indices, best_scores):
        model_category = "Diğer" if float(score) < semantic_threshold else categories[cat_idx]
        final_category, decision_source, rule_category = _resolve_category_with_priority(
            comment,
            model_category,
            float(score),
            semantic_threshold,
            keyword_rules,
        )

        final_label = _label_text(final_category, emoji_map)
        categorized[final_label].append({
            "yorum": comment,
            "skor": round(float(score), 3),
            "model_kategori": _label_text(model_category, emoji_map),
            "kural_kategori": _label_text(rule_category, emoji_map) if rule_category else "",
            "secim_kaynagi": decision_source,
        })

    result = {}
    for label in sorted(categorized, key=lambda x: len(categorized[x]), reverse=True):
        items = categorized[label]
        result[label] = {
            # DÜZELTME: yorumlar düz string listesi olarak döndürülür;
            # feedback_kaydet() ve excel_kaydet() string beklediği için.
            "yorumlar": [i["yorum"] for i in items],
            "sorun_sayısı": len(items),
            "ort_skor": round(sum(i["skor"] for i in items) / len(items), 3),
        }

    print(f"     ✓ {len(result)} kategori oluşturuldu")
    return result


class DatabaseCategorizer:
    def __init__(self, connection_string='mongodb://localhost:27017/', db_name='apple_feedback_db'):
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        self.comments_collection = self.db['comments']

    def kategorilendire(self, source=None, device_name=None, batch_size=100):
        print("\n" + "=" * 70)
        print("🧠 YORUM KATEGORİLEME - READ ONLY")
        print("=" * 70 + "\n")

        query = {
            'category': {'$exists': False},
            'device_normalize_status': 'apple'
        }
        if source:
            query['source'] = source
        if device_name:
            query['device_name'] = device_name

        unprocessed = list(self.comments_collection.find(query))
        print(f"📊 {len(unprocessed)} işlenmemiş yorum bulundu\n")

        if not unprocessed:
            print("ℹ️  Yapılacak işlem yok!")
            return {'toplam': 0, 'kategorilendirilen': 0, 'hata': 0}

        taxonomy_key, categories, category_descriptions, keyword_rules, emoji_map = _get_taxonomy(device_name)
        _compute_category_embeddings(taxonomy_key, category_descriptions)

        stats = {'toplam': len(unprocessed), 'kategorilendirilen': 0, 'hata': 0}

        for batch_start in range(0, len(unprocessed), batch_size):
            batch = unprocessed[batch_start:batch_start + batch_size]
            print(f"🔄 Batch {batch_start // batch_size + 1} işleniyor ({batch_start}-{batch_start + len(batch)})...")

            batch_comments = []
            for doc in batch:
                comment_to_process = doc.get('normalized_comment')
                if not comment_to_process:
                    original_comment = doc.get('comment', '')
                    # DÜZELTME: _safe_normalize kullan
                    comment_to_process = _safe_normalize(original_comment)
                batch_comments.append(comment_to_process)

            try:
                embeddings  = _EMBEDDER.encode(
                    batch_comments, convert_to_numpy=True, show_progress_bar=False
                )
                similarities = cosine_similarity(embeddings, _CATEGORY_EMBEDDINGS_CACHE[taxonomy_key])
                best_indices = np.argmax(similarities, axis=1)
                best_scores  = np.max(similarities, axis=1)

                for doc, cat_idx, score in zip(batch, best_indices, best_scores):
                    yorum_metni = doc.get('comment', '') or doc.get('normalized_comment', '') or ''
                    if konu_disi_mi(yorum_metni):
                        category_name = 'Platform ve Dolandırıcılık Sorunu'
                    else:
                        semantic_threshold = 0.30 if taxonomy_key == "unknown" else 0.32 if taxonomy_key == "airpods" else 0.35
                        model_category = "Diğer" if float(score) < semantic_threshold else categories[int(cat_idx)]
                        category_name, _, _ = _resolve_category_with_priority(
                            yorum_metni,
                            model_category,
                            float(score),
                            semantic_threshold,
                            keyword_rules,
                        )

                    # Read-only mod: veritabanına yazma yapılmaz, sadece sayım tutulur.
                    stats['kategorilendirilen'] += 1
                    _ = category_name, round(float(score), 3)

            except Exception as e:
                print(f"    ⚠️  Hata: {e}")
                stats['hata'] += len(batch)

        print(f"\n{'─' * 70}")
        print(f"✅ Kategorilendirilen: {stats['kategorilendirilen']}")
        print(f"⚠️  Hata: {stats['hata']}")
        print(f"{'─' * 70}\n")
        return stats

    def kapat(self):
        self.client.close()


if __name__ == "__main__":
    try:
        categorizer = DatabaseCategorizer()
        stats = categorizer.kategorilendire()
        categorizer.kapat()
    except Exception as e:
        print(f"❌ Hata: {e}")