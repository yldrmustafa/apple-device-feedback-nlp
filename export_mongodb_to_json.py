import argparse
from datetime import datetime
from pathlib import Path

from bson import json_util
from pymongo import MongoClient


SYSTEM_DATABASES = {"admin", "local", "config"}


def export_mongodb_to_json(connection_string: str, output_path: str, database_name: str | None = None) -> dict:
    client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")

    try:
        if database_name:
            database_names = [database_name]
        else:
            database_names = [name for name in client.list_database_names() if name not in SYSTEM_DATABASES]

        export_data = {
            "meta": {
                "exported_at": datetime.now().isoformat(),
                "connection_string": connection_string,
                "database_filter": database_name or "all_non_system_databases",
                "database_count": len(database_names),
            },
            "databases": {},
        }

        total_collections = 0
        total_documents = 0

        for db_name in database_names:
            db = client[db_name]
            collection_names = db.list_collection_names()

            db_payload = {
                "meta": {
                    "collection_count": len(collection_names),
                },
                "collections": {},
            }

            for collection_name in collection_names:
                collection = db[collection_name]
                documents = list(collection.find({}))
                db_payload["collections"][collection_name] = documents
                total_collections += 1
                total_documents += len(documents)

            export_data["databases"][db_name] = db_payload

        export_data["meta"]["collection_count"] = total_collections
        export_data["meta"]["document_count"] = total_documents

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json_util.dumps(export_data, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "output_path": str(output_file),
            "database_count": len(database_names),
            "collection_count": total_collections,
            "document_count": total_documents,
        }
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MongoDB verisini tek JSON dosyasına aktarır")
    parser.add_argument(
        "--uri",
        default="mongodb://localhost:27017/",
        help="MongoDB bağlantı adresi",
    )
    parser.add_argument(
        "--output",
        default="mongo_export.json",
        help="Çıktı JSON dosyası",
    )
    parser.add_argument(
        "--database",
        default=None,
        help="Sadece bu veritabanını dışa aktar (varsayılan: admin/local/config hariç tüm veritabanları)",
    )
    args = parser.parse_args()

    result = export_mongodb_to_json(args.uri, args.output, args.database)
    print(f"✅ JSON dışa aktarma tamamlandı: {result['output_path']}")
    print(f"📦 Veritabanı sayısı : {result['database_count']}")
    print(f"📚 Koleksiyon sayısı : {result['collection_count']}")
    print(f"🧾 Belge sayısı      : {result['document_count']}")
