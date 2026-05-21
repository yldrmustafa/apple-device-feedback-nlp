"""
run.py
──────
Apple feedback üretim ve onarım aracı (MongoDB read-only)

Kullanım:
  python run.py
  python run.py --repair-feedback

DÜZELTİLEN HATALAR:
  - json_veri yapısında kategoriler[kat]["yorumlar"] değeri:
    yorumlari_kumele() {"yorum":..., "skor":...} dict listesi döndürüyor,
    ama excel_kaydet() / feedback_kaydet() string bekliyordu.
    Artık kumeler zaten string listesi döndürüyor (yorum_kumeleme_v2.py düzeltildi),
    ama run.py'de de savunmalı dönüşüm eklendi.
  - islened → islenen yazım hatası düzeltildi (veri_isle içinde).
"""

import argparse
import os
import sys
import subprocess
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# UTF-8 fix
if sys.stdout.encoding != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf8", buffering=1)

from yorum_kumeleme_v2 import yorumlari_kumele, konu_disi_mi
from feedback_uret import json_kaydet, excel_kaydet, feedback_kaydet, repair_feedback_klasoru
from cihaz_tespit import cihaz_tespit
from pymongo import MongoClient

parser = argparse.ArgumentParser(description="Apple feedback üretim ve onarım aracı (MongoDB read-only)")
parser.add_argument("--repair-feedback", action="store_true", help="Mevcut feedback dosyalarını yeniden dağıt")
args, _ = parser.parse_known_args()

if args.repair_feedback:
    repair_feedback_klasoru("feedback")
    raise SystemExit(0)

os.makedirs("data",     exist_ok=True)
os.makedirs("feedback", exist_ok=True)

# ─── 1. DB ────────────────────────────────────────────────
print("\nVERİTABANI'ndan yorumlar okunuyor...")

client = None
try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    collection = client["apple_feedback_db"]["comments"]
except Exception as e:
    print(f"HATA: MongoDB bağlantı hatası: {e}")
    sys.exit(1)

docs = list(collection.find(
    {"comment": {"$exists": True, "$ne": ""}},
    {"comment": 1, "_id": 1}
))

print(f"Toplam yorum: {len(docs)}")

if client is not None:
    client.close()

# ─── 2. CİHAZ TESPİT + GRUPLAMA ──────────────────────────
print("\nYorumlarda cihaz tespit ediliyor ve gruplandırılıyor...\n")

cihaz_dict:        dict[str, list[str]] = {}
bilinmeyen_yorumlar: list[str]          = []
apple_disi  = 0
belirsiz    = 0
konu_disi   = 0

for doc in docs:
    yorum = doc.get("comment")
    if not yorum:
        continue

    sonuc = cihaz_tespit(yorum, embedding_fallback=False)

    if not sonuc.is_apple:
        apple_disi += 1
        bilinmeyen_yorumlar.append(yorum)
        continue

    if sonuc.method == "none" or sonuc.confidence < 0.40:
        belirsiz += 1
        bilinmeyen_yorumlar.append(yorum)
        continue

    if konu_disi_mi(yorum):
        konu_disi += 1
        bilinmeyen_yorumlar.append(yorum)
        continue

    cihaz = sonuc.normalized
    cihaz_dict.setdefault(cihaz, []).append(yorum)

print(f"Cihaz sayısı    : {len(cihaz_dict)}")
print(f"Apple dışı      : {apple_disi}")
print(f"Belirsiz        : {belirsiz}")
print(f"Konu dışı       : {konu_disi}")
print(f"Bulunan cihazlar: {sorted(cihaz_dict.keys())}")

# ─── 3. KATEGORİLEME ─────────────────────────────────────
print("\nOtomatik kategorileme başlıyor...\n")

tum_kumeler: dict[str, dict] = {}

for cihaz, yorum_listesi in cihaz_dict.items():
    try:
        print(f"{cihaz} analiz ediliyor ({len(yorum_listesi)} yorum)...")
        kumeler = yorumlari_kumele(yorum_listesi, cihaz_adi=cihaz)
        print(f"   {len(kumeler)} sorun kategorisi bulundu")
        tum_kumeler[cihaz] = kumeler
    except Exception as e:
        print(f"   Hata: {e}")
        import traceback
        traceback.print_exc()

toplam_yorum = len(docs)

print(f"\nToplam işlenen yorum : {toplam_yorum}")
print(f"Apple yorumları       : {sum(len(v) for v in cihaz_dict.values())}")
print(f"Bilinmeyen yorumlar   : {len(bilinmeyen_yorumlar)}")
print("Kategorileme tamamlandı!")

# ─── 4. FEEDBACK ─────────────────────────────────────────
print("\n💾 Feedback dosyaları oluşturuluyor...\n")

zaman = datetime.now().strftime("%Y%m%d_%H%M")

for cihaz, kumeler in tum_kumeler.items():
    try:
        feedback_kaydet(cihaz, kumeler)
    except Exception as e:
        print(f"❌ {cihaz} hatası: {e}")

# ─── 5. JSON + EXCEL ──────────────────────────────────────
print("Birleştirilmiş JSON ve Excel oluşturuluyor...")


def _yorumlar_listesi(kumeler_dict: dict, kat: str) -> list:
    """
    kumeler_dict[kat]["yorumlar"] içeriğini düz string listesine çevirir.
    yorumlari_kumele() string listesi döndürmeli (düzeltildi), ama
    eski veya beklenmedik formatlara karşı savunmalı dönüşüm yapılır.
    """
    raw = kumeler_dict.get(kat, {}).get("yorumlar", [])
    result = []
    for item in raw:
        if isinstance(item, dict):
            result.append(item.get("yorum", ""))
        else:
            result.append(str(item))
    return result


json_veri = {
    "meta": {
        "olusturulma_tarihi": datetime.now().isoformat(),
        "kaynak_filtresi":    "tümü",
        "toplam_yorum":       toplam_yorum,
        "apple_disi":         apple_disi,
        "belirsiz":           belirsiz,
        "benzersiz_cihaz":    len(tum_kumeler),
    },
    "cihazlar": {
        cihaz: {
            "toplam": sum(v.get("sorun_sayısı", 0) for v in kumeler.values()),
            "kategoriler": {
                # Emoji'li label'dan saf kategori adını çıkar (varsa)
                kat: {
                    "toplam":  v.get("sorun_sayısı", len(v.get("yorumlar", []))),
                    # DÜZELTME: yorumlar her zaman str listesi
                    "yorumlar": _yorumlar_listesi(kumeler, kat),
                }
                for kat, v in kumeler.items()
            },
        }
        for cihaz, kumeler in tum_kumeler.items()
    },
}

json_kaydet(json_veri, f"feedback/feedback_{zaman}.json")
excel_kaydet(json_veri, f"feedback/feedback_{zaman}.xlsx")

print("\n✔ TAMAMLANDI")

# ─── 6. BİLİNMEYENLER ────────────────────────────────────
if bilinmeyen_yorumlar:
    print(f"\nBilinmeyen yorum sayısı: {len(bilinmeyen_yorumlar)}")
    bilinmeyen_kumeler = yorumlari_kumele(bilinmeyen_yorumlar, cihaz_adi="bilinmeyen")
    feedback_kaydet("bilinmeyen", bilinmeyen_kumeler)
    print("✔ bilinmeyen feedback kaydedildi")
else:
    print("✔ Bilinmeyen yorum yok")

print("\n🔧 Feedback dosyaları yeniden dağıtılıyor...")
repair_feedback_klasoru("feedback")
print("✔ Feedback onarımı tamamlandı")

# ─── 7. DASHBOARD (isteğe bağlı) ──────────────────────────
# subprocess.Popen([sys.executable, "-m", "streamlit", "run", "dashboard.py"])
# print("✔ http://localhost:8501")