"""
cihaz_tespit.py
───────────────
Yorum metninden Apple cihaz modelini tespit eder.

Strateji (hız sırasıyla):
  1. Regex/kural tabanlı  →  hızlı, yüksek güven
  2. Anahtar kelime eşleme →  orta güven
  3. Embedding fallback    →  yavaş ama yakalayıcı

Dönüş:
  {
      "raw":        "iphon 15 pro",          # metinde bulunan ham ifade
      "normalized": "iPhone 15 Pro",         # standart form
      "family":     "iPhone",                # üst kategori
      "confidence": 0.95,                    # 0.0 – 1.0
      "method":     "regex",                 # regex | keyword | embedding | none
      "is_apple":   True
  }

DÜZELTİLEN HATALAR:
  - _on_isle() Türkçe karakterleri ASCII'ye çevirmeden önce işliyordu;
    ı/İ/ğ/ş/ç/ö/ü artık doğru sırayla dönüştürülüyor.
  - iPhone 14 Pro Max regex kuralı eksikti; eklendi.
  - APPLE_PREFIX ile başlayan X/XS/XR kuralları çok geniş eşleşiyordu
    (örn. "apple xs max" → "iPhone XS Max" ama "xs" tek başına da eşleşebilir).
    Bu kurallar IPHONE_PREFIX gerektiren versiyonlarla birleştirildi,
    APPLE_PREFIX'li bağımsız X kuralları kaldırıldı.
  - _TYPO_MAP anahtarları ASCII normalize sonrası çalışacak şekilde güncellendi.
"""

import re
import unicodedata
from typing import Optional
from dataclasses import dataclass, field, asdict

# ─────────────────────────────────────────────────────────
# 0. VERİ MODELİ
# ─────────────────────────────────────────────────────────

@dataclass
class CihazSonuc:
    raw: str = ""
    normalized: str = ""
    family: str = ""
    confidence: float = 0.0
    method: str = "none"      # regex | keyword | embedding | none
    is_apple: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────
# 1. REGEX KURALLARI
#    Sıralama KRİTİK: daha spesifik olanlar önce gelmeli!
# ─────────────────────────────────────────────────────────

# IPHONE_PREFIX: "iphone", "iphane", "appel" gibi varyasyonları yakalar.
# _on_isle() sonrası metin ASCII + küçük harf olduğundan türkçe harf gerekmez.
IPHONE_PREFIX = r"(?:i\s*ph[oa]?n[ei]?|a\s*p{1,2}[el]e?)"
# APPLE_PREFIX: yalnızca "apple" sözcüğü + opsiyonel boşluk
APPLE_PREFIX  = r"(?:apple\s*)?"

_REGEX_RULES: list[tuple] = [

    # ── iPhone 17 ────────────────────────────────────────
    (fr"{IPHONE_PREFIX}\s*17\s*pro\s*max",  "iPhone 17 Pro Max",  "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*17\s*pro",        "iPhone 17 Pro",      "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*17\s*plus",       "iPhone 17 Plus",     "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*17",              "iPhone 17",          "iPhone", 0.97),

    # ── iPhone 16 ────────────────────────────────────────
    (fr"{IPHONE_PREFIX}\s*16\s*pro\s*max",  "iPhone 16 Pro Max",  "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*16\s*pro",        "iPhone 16 Pro",      "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*16\s*plus",       "iPhone 16 Plus",     "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*16",              "iPhone 16",          "iPhone", 0.97),

    # ── iPhone 15 ────────────────────────────────────────
    (fr"{IPHONE_PREFIX}\s*15\s*pro\s*max",  "iPhone 15 Pro Max",  "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*15\s*pro",        "iPhone 15 Pro",      "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*15\s*plus",       "iPhone 15 Plus",     "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*15",              "iPhone 15",          "iPhone", 0.97),

    # ── iPhone 14 ────────────────────────────────────────
    # DÜZELTME: Pro Max, Pro önce gelmeli; orijinalde Pro Max eksikti.
    (fr"{IPHONE_PREFIX}\s*14\s*pro\s*max",  "iPhone 14 Pro Max",  "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*14\s*pro",        "iPhone 14 Pro",      "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*14\s*(?:plus|\+)","iPhone 14 Plus",     "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*14",              "iPhone 14",          "iPhone", 0.97),

    # ── iPhone 13 ────────────────────────────────────────
    (fr"{IPHONE_PREFIX}\s*13\s*pro\s*max",  "iPhone 13 Pro Max",  "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*13\s*pro",        "iPhone 13 Pro",      "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*13\s*mini",       "iPhone 13 Mini",     "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*13",              "iPhone 13",          "iPhone", 0.97),

    # ── iPhone 12 ────────────────────────────────────────
    (fr"{IPHONE_PREFIX}\s*12\s*pro\s*max",  "iPhone 12 Pro Max",  "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*12\s*pro",        "iPhone 12 Pro",      "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*12\s*mini",       "iPhone 12 Mini",     "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*12",              "iPhone 12",          "iPhone", 0.97),

    # ── iPhone 11 ────────────────────────────────────────
    (fr"{IPHONE_PREFIX}\s*11\s*pro\s*max",  "iPhone 11 Pro Max",  "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*11\s*pro",        "iPhone 11 Pro",      "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*11",              "iPhone 11",          "iPhone", 0.97),

    # ── iPhone X serisi ──────────────────────────────────
    # DÜZELTME: Yalnızca IPHONE_PREFIX ile; APPLE_PREFIX'li bağımsız kurallar
    # "apple xs" gibi belirsiz eşleşmelere yol açıyordu.
    (fr"{IPHONE_PREFIX}\s*x\s*s\s*max",     "iPhone XS Max",      "iPhone", 0.98),
    (fr"{IPHONE_PREFIX}\s*x\s*s\b",         "iPhone XS",          "iPhone", 0.97),
    (fr"{IPHONE_PREFIX}\s*x\s*r\b",         "iPhone XR",          "iPhone", 0.97),
    # "iphone x" — tek 'x' harfi: model numarasından önce word boundary şart
    (fr"{IPHONE_PREFIX}\s*x\b",             "iPhone X",           "iPhone", 0.96),

    # ── iPhone SE ────────────────────────────────────────
    (fr"{IPHONE_PREFIX}\s*se\s*[34]",       "iPhone SE 3",        "iPhone", 0.97),
    (fr"{IPHONE_PREFIX}\s*se\b",            "iPhone SE",          "iPhone", 0.95),

    # ── iPhone 8 / 7 / 6 ─────────────────────────────────
    (fr"{IPHONE_PREFIX}\s*8\s*plus",        "iPhone 8 Plus",      "iPhone", 0.97),
    (fr"{IPHONE_PREFIX}\s*8\b",             "iPhone 8",           "iPhone", 0.96),
    (fr"{IPHONE_PREFIX}\s*7\s*plus",        "iPhone 7 Plus",      "iPhone", 0.97),
    (fr"{IPHONE_PREFIX}\s*7\b",             "iPhone 7",           "iPhone", 0.96),
    (fr"{IPHONE_PREFIX}\s*6s\s*plus",       "iPhone 6s Plus",     "iPhone", 0.97),
    (fr"{IPHONE_PREFIX}\s*6s\b",            "iPhone 6s",          "iPhone", 0.97),
    (fr"{IPHONE_PREFIX}\s*6\s*plus",        "iPhone 6 Plus",      "iPhone", 0.97),
    (fr"{IPHONE_PREFIX}\s*6\b",             "iPhone 6",           "iPhone", 0.96),

    # Genel iPhone (model belirtilmemiş)
    (r"i\s*ph[oa]?n[ei]",                   "iPhone",             "iPhone", 0.75),

    # ── iPad ─────────────────────────────────────────────
    (fr"{APPLE_PREFIX}i\s*pad\s*pro\s*m\d",               "iPad Pro",      "iPad", 0.98),
    (fr"{APPLE_PREFIX}i\s*pad\s*pro\s*1[12]\s*[.']?\s*9", "iPad Pro 12.9", "iPad", 0.98),
    (fr"{APPLE_PREFIX}i\s*pad\s*pro\s*1[01]\s*[.']?\s*5", "iPad Pro 10.5", "iPad", 0.98),
    (fr"{APPLE_PREFIX}i\s*pad\s*pro",                      "iPad Pro",      "iPad", 0.95),
    (fr"{APPLE_PREFIX}i\s*pad\s*air\s*m\d",               "iPad Air",      "iPad", 0.98),
    (fr"{APPLE_PREFIX}i\s*pad\s*air\s*[2-6]",             "iPad Air",      "iPad", 0.97),
    (fr"{APPLE_PREFIX}i\s*pad\s*air",                      "iPad Air",      "iPad", 0.95),
    (fr"{APPLE_PREFIX}i\s*pad\s*mini\s*[2-7]",            "iPad Mini",     "iPad", 0.97),
    (fr"{APPLE_PREFIX}i\s*pad\s*mini",                     "iPad Mini",     "iPad", 0.95),
    (fr"{APPLE_PREFIX}i\s*pad\s*10",                       "iPad 10",       "iPad", 0.97),
    (fr"{APPLE_PREFIX}i\s*pad\s*[6-9]",                   "iPad",          "iPad", 0.97),
    (fr"{APPLE_PREFIX}i\s*pad",                            "iPad",          "iPad", 0.75),

    # ── MacBook ──────────────────────────────────────────
    (fr"{APPLE_PREFIX}macbook\s*pro\s*m\d",               "MacBook Pro",   "Mac", 0.98),
    (fr"{APPLE_PREFIX}macbook\s*pro\s*1[3456789]\s*inc",  "MacBook Pro",   "Mac", 0.97),
    (fr"{APPLE_PREFIX}macbook\s*pro\s*1[3456789]",        "MacBook Pro",   "Mac", 0.97),
    (fr"{APPLE_PREFIX}macbook\s*pro",                      "MacBook Pro",   "Mac", 0.95),
    (fr"{APPLE_PREFIX}macbook\s*air\s*m\d",               "MacBook Air",   "Mac", 0.98),
    (fr"{APPLE_PREFIX}macbook\s*air",                      "MacBook Air",   "Mac", 0.95),
    (fr"{APPLE_PREFIX}macbook",                            "MacBook",       "Mac", 0.85),

    # ── Mac masaüstü ─────────────────────────────────────
    (fr"{APPLE_PREFIX}mac\s*studio",                       "Mac Studio",    "Mac", 0.97),
    (fr"{APPLE_PREFIX}mac\s*mini",                         "Mac Mini",      "Mac", 0.97),
    (fr"{APPLE_PREFIX}mac\s*pro",                          "Mac Pro",       "Mac", 0.96),
    (fr"{APPLE_PREFIX}imac\s*pro",                         "iMac Pro",      "Mac", 0.97),
    (fr"{APPLE_PREFIX}imac\s*m\d",                         "iMac",          "Mac", 0.98),
    (fr"{APPLE_PREFIX}imac\s*2[0-9]",                      "iMac",          "Mac", 0.97),
    (fr"{APPLE_PREFIX}imac",                               "iMac",          "Mac", 0.90),

    # ── Apple Watch ──────────────────────────────────────
    (fr"(?:apple\s*)?watch\s*series\s*10",             "Apple Watch Series 10", "Apple Watch", 0.98),
    (fr"(?:apple\s*)?watch\s*series\s*9",              "Apple Watch Series 9",  "Apple Watch", 0.98),
    (fr"(?:apple\s*)?watch\s*series\s*8",              "Apple Watch Series 8",  "Apple Watch", 0.98),
    (fr"(?:apple\s*)?watch\s*ultra\s*[12]",            "Apple Watch Ultra 2",   "Apple Watch", 0.98),
    (fr"(?:apple\s*)?watch\s*ultra",                    "Apple Watch Ultra",     "Apple Watch", 0.97),
    (fr"(?:apple\s*)?watch\s*se\b\s*[23]",            "Apple Watch SE",        "Apple Watch", 0.97),
    (fr"(?:apple\s*)?watch\s*se\b",                    "Apple Watch SE",        "Apple Watch", 0.95),
    (fr"{APPLE_PREFIX}apple\s*watch\s*(series\s*)?10",     "Apple Watch Series 10", "Apple Watch", 0.98),
    (fr"{APPLE_PREFIX}apple\s*watch\s*(series\s*)?9",      "Apple Watch Series 9",  "Apple Watch", 0.98),
    (fr"{APPLE_PREFIX}apple\s*watch\s*(series\s*)?8",      "Apple Watch Series 8",  "Apple Watch", 0.98),
    (fr"{APPLE_PREFIX}apple\s*watch\s*(series\s*)?[1-7]",  "Apple Watch",           "Apple Watch", 0.97),
    (fr"{APPLE_PREFIX}apple\s*watch\s*ultra\s*[12]",       "Apple Watch Ultra 2",   "Apple Watch", 0.98),
    (fr"{APPLE_PREFIX}apple\s*watch\s*ultra",              "Apple Watch Ultra",     "Apple Watch", 0.97),
    (fr"{APPLE_PREFIX}apple\s*watch\s*se\b\s*[23]",        "Apple Watch SE",        "Apple Watch", 0.97),
    (fr"{APPLE_PREFIX}apple\s*watch\s*se\b",               "Apple Watch SE",        "Apple Watch", 0.95),
    (fr"{APPLE_PREFIX}apple\s*watch",                       "Apple Watch",           "Apple Watch", 0.85),

    # ── AirPods ───────────────────────────────────────────
    (fr"{APPLE_PREFIX}airpods?\s*pro\s*3(?:nd)?",          "AirPods Pro 3", "AirPods", 0.98),
    (fr"{APPLE_PREFIX}airpods?\s*pro\s*[23]",              "AirPods Pro 2", "AirPods", 0.98),
    (fr"{APPLE_PREFIX}airpods?\s*pro",                     "AirPods Pro",   "AirPods", 0.96),
    (fr"{APPLE_PREFIX}airpods?\s*max",                     "AirPods Max",   "AirPods", 0.97),
    (fr"{APPLE_PREFIX}airpods?\s*[234]",                   "AirPods",       "AirPods", 0.97),
    (fr"{APPLE_PREFIX}airpods?",                           "AirPods",       "AirPods", 0.85),

    # ── Apple TV ─────────────────────────────────────────
    (fr"{APPLE_PREFIX}apple\s*tv\s*4k",                   "Apple TV 4K",   "Apple TV", 0.97),
    (fr"{APPLE_PREFIX}apple\s*tv",                         "Apple TV",      "Apple TV", 0.90),

    # ── HomePod ──────────────────────────────────────────
    (fr"{APPLE_PREFIX}homepod\s*mini",                     "HomePod Mini",  "HomePod", 0.97),
    (fr"{APPLE_PREFIX}homepod",                            "HomePod",       "HomePod", 0.90),
]

# ─────────────────────────────────────────────────────────
# 2. TYPO MAP  (ASCII normalize sonrası uygulanır)
# ─────────────────────────────────────────────────────────

_TYPO_MAP = {
    # Türkçe harfler zaten _on_isle'de ASCII'ye çevrildiğinden burada ASCII form kullan
    "iphone15":     "iphone 15",
    "iphone14":     "iphone 14",
    "iphone13":     "iphone 13",
    "iphone12":     "iphone 12",
    "iphone11":     "iphone 11",
    "applewatch":   "apple watch",
    "appletv":      "apple tv",
    "macbookair":   "macbook air",
    "macbookpro":   "macbook pro",
    "airpod":       "airpods",
    "aipods":       "airpods",
}

# ─────────────────────────────────────────────────────────
# 3. SİNYAL PARELTERNLERİ
# ─────────────────────────────────────────────────────────

_APPLE_DEVICE_SIGNAL_PATTERNS = [
    r"\biphone\b",
    r"\bipad\b",
    r"\bmacbook\b",
    r"\bimac\b",
    r"\bairpods?\b",
    r"\bhomepod\b",
    r"\bapple\s*watch\b",
    r"\bwatch\s*ultra\b",
    r"\bwatch\s*se\b",
]

_APPLE_BRAND_SIGNAL_PATTERNS = _APPLE_DEVICE_SIGNAL_PATTERNS + [
    r"\bapple\s*id\b",
    r"\bicloud\b",
    r"\bapp\s*store\b",
    r"\bitunes\b",
    r"\bapple\s*online\s*store\b",
    r"\bapple\s*com\b",
    r"\bapple\s*support\b",
    r"\bgenius\s*bar\b",
    r"\bapple\s*destek\b",
]

_NON_APPLE_SIGNALS = [
    r"turk\s*telekom", r"turkcell", r"vodafone", r"samsung", r"huawei",
    r"xiaomi", r"oppo", r"realme", r"sony", r"lg\s", r"nokia", r"motorola",
    r"lenovo", r"asus", r"acer", r"dell", r"hp\s", r"windows", r"android",
    r"galaxy\s*s", r"galaxy\s*a", r"pixel\s*[0-9]", r"playstation", r"xbox",
]


# ─────────────────────────────────────────────────────────
# 4. EMBEDDING FALLBACK
# ─────────────────────────────────────────────────────────

_EMBEDDER = None
_EMBEDDING_LOADED = False
_CANDIDATE_EMBS = None


def _load_embedder():
    global _EMBEDDER, _EMBEDDING_LOADED
    if _EMBEDDING_LOADED:
        return
    try:
        from sentence_transformers import SentenceTransformer
        import os
        print("  ⏳ Embedding modeli yükleniyor (fallback için)...")
        _EMBEDDER = SentenceTransformer(
            'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
            device='cpu',
            cache_folder=os.path.expanduser('~/.cache/huggingface/hub')
        )
        print("  ✓ Embedding hazır!")
    except Exception as e:
        print(f"  ⚠️  Embedding yüklenemedi: {e}")
    _EMBEDDING_LOADED = True


# ─────────────────────────────────────────────────────────
# 5. YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────────────────

def _on_isle(metin: str) -> str:
    """
    Metni regex eşleşmesine hazırla.

    DÜZELTME: Orijinal kodda _TYPO_MAP Türkçe karakter içeriyordu ama
    ASCII encode sonrası bu karakterler düşüyordu — hiçbir typo eşleşmiyordu.
    Şimdi:
      1. Türkçe büyük harf özel durumları (İ→i, I→i)
      2. Küçük harfe çevir
      3. Türkçe küçük harfler → ASCII (ı→i, ğ→g, ş→s, ç→c, ö→o, ü→u)
      4. NFKD normalize → ASCII encode
      5. Typo map (artık ASCII'ye karşı çalışır)
      6. Noktalama sadeleştir
    """
    m = metin
    # Türkçe büyük harf özel durumları
    m = m.replace("İ", "i").replace("I", "i")
    m = m.lower()
    # Türkçe küçük harfleri ASCII'ye çevir
    _TR = str.maketrans("ığşçöü", "igscou")
    m = m.translate(_TR)
    # ı → i (translate ile map edilemez, ayrıca işle)
    m = m.replace("ı", "i")
    m = unicodedata.normalize("NFKD", m).encode("ascii", "ignore").decode("ascii")
    # Noktalama/ayırıcı sadeleştir (typo map'ten önce — boşluklar yerine gelsin)
    m = re.sub(r"[^a-z0-9]+", " ", m)
    m = re.sub(r"\s+", " ", m).strip()
    # Typo düzeltme: word boundary ile — "airpod" → "airpods" ama
    # "airpods" içindeki "airpod" kısmını eşleştirmesin.
    for wrong, right in _TYPO_MAP.items():
        m = re.sub(r"\b" + re.escape(wrong) + r"\b", right, m)
    return m


def _signal_var_mi(metin: str, patterns: list[str]) -> bool:
    m = _on_isle(metin)
    return any(re.search(p, m) for p in patterns)


def _apple_device_var_mi(metin: str) -> bool:
    return _signal_var_mi(metin, _APPLE_DEVICE_SIGNAL_PATTERNS)


def _apple_brand_var_mi(metin: str) -> bool:
    return _signal_var_mi(metin, _APPLE_BRAND_SIGNAL_PATTERNS)


def _apple_disi_mi(metin: str) -> bool:
    """Metin açıkça Apple dışı bir ürün/hizmet mi?"""
    if _apple_brand_var_mi(metin):
        return False
    m = _on_isle(metin)
    return any(re.search(p, m) for p in _NON_APPLE_SIGNALS)


# ─────────────────────────────────────────────────────────
# 6. TESPİT FONKSİYONLARI
# ─────────────────────────────────────────────────────────

def _regex_tespit(metin: str) -> Optional[CihazSonuc]:
    """Kural tabanlı hızlı tespit (method=regex)."""
    m = _on_isle(metin)
    for pattern, normalized, family, conf in _REGEX_RULES:
        match = re.search(pattern, m)
        if match:
            return CihazSonuc(
                raw=match.group(0).strip(),
                normalized=normalized,
                family=family,
                confidence=conf,
                method="regex",
                is_apple=True,
            )
    return None


def _keyword_tespit(metin: str) -> Optional[CihazSonuc]:
    """Sayısal model referansı olmayan yorumlar için anahtar kelime eşleme."""
    m = _on_isle(metin)
    patterns = [
        (r"\bapple\s*watch\b", "Apple Watch", "Apple Watch", 0.90),
    ]
    for pat, normalized, family, conf in patterns:
        match = re.search(pat, m)
        if match:
            return CihazSonuc(
                raw=match.group(0),
                normalized=normalized,
                family=family,
                confidence=conf,
                method="keyword",
                is_apple=True,
            )
    return None


def _embedding_tespit(metin: str) -> Optional[CihazSonuc]:
    """Embedding tabanlı fallback. Sadece kısa/belirsiz yorumlar için."""
    _load_embedder()
    if _EMBEDDER is None:
        return None

    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity

    candidates = [
        ("iPhone",      "iPhone",      "iPhone"),
        ("iPad",        "iPad",        "iPad"),
        ("MacBook",     "MacBook",     "Mac"),
        ("iMac",        "iMac",        "Mac"),
        ("Apple Watch", "Apple Watch", "Apple Watch"),
        ("AirPods",     "AirPods",     "AirPods"),
        ("AirPods Pro", "AirPods Pro", "AirPods"),
        ("HomePod",     "HomePod",     "HomePod"),
    ]
    labels     = [c[0] for c in candidates]
    normalized = [c[1] for c in candidates]
    families   = [c[2] for c in candidates]

    passages = [f"passage: Bu bir {l} şikayetidir" for l in labels]
    query    = f"query: {metin[:300]}"

    try:
        q_emb = _EMBEDDER.encode([query], normalize_embeddings=True)
        p_emb = _EMBEDDER.encode(passages, normalize_embeddings=True)
        sims  = cosine_similarity(q_emb, p_emb)[0]
        best  = int(np.argmax(sims))
        score = float(sims[best])

        if score < 0.55:
            return None

        return CihazSonuc(
            raw=labels[best],
            normalized=normalized[best],
            family=families[best],
            confidence=round(score, 3),
            method="embedding",
            is_apple=True,
        )
    except Exception:
        return None


# ─────────────────────────────────────────────────────────
# 7. ANA FONKSİYON
# ─────────────────────────────────────────────────────────

def cihaz_tespit(
    yorum: str,
    embedding_fallback: bool = True,
    keyword_fallback: bool = True,
) -> CihazSonuc:
    """
    Yorum metninden Apple cihazını tespit et.

    Args:
        yorum:              Ham yorum metni
        embedding_fallback: Düşük güvende embedding'e düş (yavaş)
        keyword_fallback:   Regex tutmazsa kelime tabanlı dene

    Returns:
        CihazSonuc dataclass (is_apple=False → Apple dışı yorum)
    """
    if not yorum or not yorum.strip():
        return CihazSonuc(method="none")

    # Apple dışı sinyal varsa erken çık; Apple marka/cihaz sinyali varsa geçme.
    if _apple_disi_mi(yorum) and not _apple_brand_var_mi(yorum):
        return CihazSonuc(
            raw="",
            normalized="apple_disi",
            family="apple_disi",
            confidence=0.95,
            method="regex",
            is_apple=False,
        )

    # 1. Regex
    sonuc = _regex_tespit(yorum)
    if sonuc and sonuc.confidence >= 0.85:
        return sonuc

    # 2. Keyword
    if keyword_fallback:
        kw = _keyword_tespit(yorum)
        if kw:
            if sonuc is None or kw.confidence > sonuc.confidence:
                sonuc = kw

    # 3. Embedding fallback
    if embedding_fallback and (sonuc is None or sonuc.confidence < 0.60):
        emb = _embedding_tespit(yorum)
        if emb:
            sonuc = emb

    return sonuc or CihazSonuc(method="none")


def toplu_tespit(
    yorumlar: list[str],
    embedding_fallback: bool = True,
) -> list[CihazSonuc]:
    """Birden fazla yorumu sırayla tespit et."""
    return [cihaz_tespit(y, embedding_fallback=embedding_fallback) for y in yorumlar]