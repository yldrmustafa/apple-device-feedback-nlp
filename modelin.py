from sentence_transformers import SentenceTransformer

# Modeli indirir
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')

# Modeli bilgisayarınızda bir klasöre kaydeder
model.save(r'D:\Bitirme_Projesi\apple-device-feedback-nlp\models\all-MiniLM-L6-v2\modelv2base')