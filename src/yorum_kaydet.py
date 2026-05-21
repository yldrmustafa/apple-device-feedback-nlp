"""
Yorumları MongoDB'ye kaydetme modülü
Sikayet vb.'den çekilen yorumları veritabanına kaydeder.
"""

import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError
import hashlib
from complaint_normalizer import normalize_complaint

class CommentSaver:
    """MongoDB'ye yorumları kaydeden sınıf"""
    
    def __init__(self, connection_string='mongodb://localhost:27017/', db_name='apple_feedback_db'):
        """
        Database bağlantısını başlat
        
        Args:
            connection_string (str): MongoDB bağlantı adresi
            db_name (str): Kullanılacak database adı
        """
        try:
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            
            self.db = self.client[db_name]
            self.comments_collection = self.db['comments']
            
            # İndexleri oluştur
            self.comments_collection.create_index([('source', 1), ('comment_hash', 1)], unique=True)
            
        except ServerSelectionTimeoutError:
            print(f"❌ MongoDB bağlanamadı: {connection_string}")
            raise
    
    def kaydet(self, yorum, cihaz, source='sikayetvar', url=None):
        """
        Tek yorum kaydet
        
        Args:
            yorum (str): Yorum metni
            cihaz (str): Cihaz adı
            source (str): Yorum kaynağı
            url (str): Kaynak URL'si
        
        Returns:
            bool: Başarılı mı?
        """
        try:
            # Yorumu normalleştir. Hash bu normalleşmiş hal üzerinden alınır.
            # Bu sayede küçük farklar (boşluk, noktalama) olan aynı yorumlar duplicate sayılır.
            normalized_comment = normalize_complaint(yorum)
            comment_hash = hashlib.md5(f"{source}{normalized_comment}".encode()).hexdigest()
            
            document = {
                'source': source,
                'comment': yorum, # Orijinal yorumu koru
                'comment_hash': comment_hash,
                'normalized_comment': normalized_comment, # İşleme için normalleşmiş hali
                'device_name': cihaz,
                'url': url,
                'scraped_at': datetime.now(),
                'processed': False,
                'category': None,
                'cluster_id': None
            }
            
            self.comments_collection.insert_one(document)
            return True
            
        except DuplicateKeyError:
            return False
    
    def kaydet_toplu(self, yorumlar, cihaz, source='sikayetvar'):
        """
        Birden fazla yorum kaydet (toplu işlem)
        
        Args:
            yorumlar (list): Yorum listesi
            cihaz (str): Cihaz adı
            source (str): Yorum kaynağı
        
        Returns:
            dict: {eklenen, duplicate}
        """
        stats = {'eklenen': 0, 'duplicate': 0}
        
        for yorum in yorumlar:
            if self.kaydet(yorum, cihaz, source):
                stats['eklenen'] += 1
            else:
                stats['duplicate'] += 1
        
        return stats
    
    def kapat(self):
        """Veritabanı bağlantısını kapat"""
        self.client.close()


# Global instance
_saver = None

def kaydet_yorum(yorum, cihaz, source='sikayetvar', url=None):
    """Tek yorum kaydet (shortcut fonksiyon)"""
    global _saver
    if _saver is None:
        _saver = CommentSaver()
    
    return _saver.kaydet(yorum, cihaz, source, url)


def kaydet_yorumlar(yorumlar, cihaz, source='sikayetvar'):
    """Birden fazla yorum kaydet (shortcut fonksiyon)"""
    global _saver
    if _saver is None:
        _saver = CommentSaver()
    
    return _saver.kaydet_toplu(yorumlar, cihaz, source)
