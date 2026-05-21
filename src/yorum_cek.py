
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests
import re
from urllib.parse import urljoin

def _detay_linklerini_topla(driver, base_url):
    linkler = set()

    # Kart içindeki linkleri topla
    adaylar = driver.find_elements(
        By.XPATH,
        "//div[contains(@class,'complaint')]//a[@href] | //article//a[@href]"
    )

    for a in adaylar:
        href = (a.get_attribute("href") or "").strip()
        if not href:
            continue

        # Genelde detay linkleri daha uzun ve tekil olur; filtreyi esnek tutuyoruz
        if "sikayetvar.com" not in href:
            href = urljoin(base_url, href)

        if "sikayetvar.com" in href:
            linkler.add(href)

    return list(linkler)

def _detaydan_tam_yorum_cek(driver, detay_url):
    ok = _safe_get(driver, detay_url)
    if not ok:
        raise RuntimeError(f"Detay sayfası yüklenemedi: {detay_url}")

    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'description')] | //article | //main")
        )
    )

    tum_devamini_ac(driver)
    time.sleep(0.5)

    # Detay sayfasında en uzun aday metni seç
    adaylar = driver.find_elements(
        By.XPATH,
        "//div[contains(@class,'complaint-description')]"
        " | //div[contains(@class,'description')]"
        " | //article//p"
    )

    metinler = []
    for el in adaylar:
        txt = _metni_normallestir(el.text)
        if len(txt) > 40:
            metinler.append(txt)

    if not metinler:
        return ""

    # En uzun metin genelde ana şikayet metni
    return max(metinler, key=len)
def _metni_normallestir(yorum):
    # Satir kirilimlarini tek bosluga indir, metni oldugu gibi koru.
    return re.sub(r"\s+", " ", yorum).strip()


def _karttan_yorum_al(kart):
    """Geriye uyumluluk icin dursun; aktif akista kullanilmiyor."""
    txt = _metni_normallestir(kart.text)
    return txt if len(txt) > 10 else ""
def yorumlari_cek(url, max_sayfa=5, start_page=1):
    """Yorumları çek. Belirtilen sayfa sayısı kadar çeker.
    
    Parametreler:
        url (str): Hedef URL
        max_sayfa (int): En fazla kaç sayfa çekecek (varsayılan: 5)
        start_page (int): Hangi sayfadan başlayacak (varsayılan: 1)
    """
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    tum_yorumlar = set()

    try:
        for sayfa in range(start_page, max_sayfa + 1):
            target_url = f"{url}?page={sayfa}"
            print(f"📄 Sayfa {sayfa} çekiliyor: {target_url}")
            
            ok = _safe_get(driver, target_url)
            if not ok:
                print(f"   ❌ Sayfa {sayfa}: yüklenemedi, atlanıyor")
                continue

            # --- Çerez veya Reklam kapatma (Varsa) ---
            try:
                # Bazı sitelerde çıkan 'Kabul Et' butonunu atlamak için
                cookie_button = driver.find_elements(By.XPATH, "//button[contains(text(),'Kabul Et')] | //div[@class='policy-close']")
                if cookie_button:
                    cookie_button[0].click()
            except:
                pass

            # --- Bekleme Kısmı ---
            # Sadece 'complaint-description' değil, daha genel bir 'complaint-card' bekleyelim
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//article[contains(@class,'complaint-card')] | //div[contains(@class,'complaint')]"))
                )
            except TimeoutException:
                print(f"   ⚠️  Sayfa {sayfa}: Elementler bulunamadı - sayfalar tükendi")
                break

            sayfayi_scroll_et(driver)
            tum_devamini_ac(driver)
            
            time.sleep(2) # İçeriğin açılması için biraz daha fazla zaman
            detay_linkleri = _detay_linklerini_topla(driver, url)

            for detay_url in detay_linkleri:
                try:
                    tam_yorum = _detaydan_tam_yorum_cek(driver, detay_url)
                    if len(tam_yorum) > 40:
                        tum_yorumlar.add(tam_yorum)
                except Exception:
                  continue
            # Sayfada en iyi kapsama bu selector ile geliyor: complaint altindaki p metinleri.
            yorum_elements = driver.find_elements(By.XPATH, "//div[contains(@class,'complaint')]//p")
            for el in yorum_elements:
                yorum = _metni_normallestir(el.text)
                if len(yorum) > 20:
                    tum_yorumlar.add(yorum)

            print(f"   ✓ Sayfa {sayfa} tamamlandı. Toplam: {len(tum_yorumlar)} yorum")

        return list(tum_yorumlar)
    finally:
        driver.quit()

def sayfayi_scroll_et(driver):
    # Sayfayı yavaşça scroll etmek bazen dinamik içeriği daha iyi tetikler
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)


def _safe_get(driver, url, max_retries=3, backoff=2):
    """Try driver.get with retries. If it fails due to connection/DNS errors,
    attempt a plain requests.get and write HTML into the driver's document.
    Returns True on success, False otherwise.
    """
    for attempt in range(1, max_retries + 1):
        try:
            driver.get(url)
            return True
        except WebDriverException as e:
            msg = str(e)
            # Geçici ağ hataları: retry yap
            if 'ERR_NAME_NOT_RESOLVED' in msg or 'ERR_CONNECTION_RESET' in msg or 'net::ERR' in msg:
                wait = backoff * attempt
                print(f"   ⚠️  Ağ hatası (deneme {attempt}): {msg.splitlines()[0] if msg.splitlines() else msg[:50]} — {wait}s sonra retry")
                time.sleep(wait)
                continue
            else:
                # Diğer hatalar: bir kez daha dene
                time.sleep(1)
                continue

    # Webdriver başarısız olursa, requests fallback'ini dene
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200 and resp.text:
            try:
                # HTML'yi tarayıcıya yükle
                driver.get("about:blank")
                driver.execute_script("document.open();document.write(arguments[0]);document.close();", resp.text)
                return True
            except Exception:
                return False
        else:
            return False
    except Exception:
        return False

def tum_devamini_ac(driver):
    """ 'Devamını Oku' butonlarını bulup JavaScript ile tıklar. """
    try:
        # Şikayetvar için güncel buton yapısı
        buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Devamını Oku')] | //span[contains(@class,'read-more')]")
        for btn in buttons:
            try:
                # Ekrana getir ve tıkla
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(0.1)
                driver.execute_script("arguments[0].click();", btn)
            except:
                continue
    except Exception as e:
        print(f"Buton açma hatası: {e}")


if __name__ == "__main__":
    import os
    import json
    from yorum_kaydet import CommentSaver
    
    # Config dosyasını yükle
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    
    if not os.path.exists(config_path):
        print(f"❌ Hata: Config dosyası bulunamadı: {config_path}")
        exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        url_listesi = json.load(f)
    
    # Database bağlantısını aç
    try:
        saver = CommentSaver()
        print("✅ MongoDB bağlantısı başarılı\n")
    except Exception as e:
        print(f"❌ MongoDB bağlantı hatası: {e}")
        exit(1)
    
    print("=" * 70)
    print("🔍 ŞIKAYETVAR YORUM ÇEKME - MongoDB'ye Kaydetme")
    print("=" * 70)
    print(f"\n📋 Toplam {len(url_listesi)} URL bulundu\n")
    
    toplam_eklenen = 0
    toplam_duplicate = 0
    
    for idx, url in enumerate(url_listesi, 1):
        cihaz_adi = url.split("/")[-1]
        
        print(f"[{idx}/{len(url_listesi)}] 🌐 {cihaz_adi}: ", end="", flush=True)
        
        try:
            # Belirtilen sayfa sayısı kadar çek (22 sayfa)
            yorumlar = yorumlari_cek(url, max_sayfa=5, start_page=1)
            
            # MongoDB'ye kaydet
            stats = saver.kaydet_toplu(yorumlar, cihaz_adi, source='sikayetvar')
            
            toplam_eklenen += stats['eklenen']
            toplam_duplicate += stats['duplicate']
            
            print(f"✅ {stats['eklenen']} eklendi")
            if stats['duplicate'] > 0:
                print(f"         ℹ️  {stats['duplicate']} duplicate")
            
        except Exception as e:
            print(f"❌ Hata: {e}\n")
    
    # Sonuç
    print(f"\n{'=' * 70}")
    print("📊 SONUÇLAR")
    print(f"{'=' * 70}\n")
    print(f"✅ Eklenen: {toplam_eklenen}")
    print(f"ℹ️  Duplicate: {toplam_duplicate}")
    print(f"💾 Toplam MongoDB'de: {saver.comments_collection.count_documents({})}\n")
    
    saver.kapat()
    
    print("✅ Yorum çekme tamamlandı!\n")
      