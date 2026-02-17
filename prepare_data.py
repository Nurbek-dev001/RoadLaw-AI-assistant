import json
import os
from pathlib import Path
from typing import List

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("⚠️  Warning: chromadb not installed. Run: pip install chromadb")

def load_pdd_data(data_path: str) -> List[dict]:
    """Load ПДД rules from JSON file"""
    data_path = Path(data_path)
    if not data_path.exists():
        # Try to find data relative to this script
        script_dir = Path(__file__).parent.parent
        data_path = script_dir / "data" / "pdd_sample.json"
    
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['rules']

def prepare_documents(rules: List[dict]) -> tuple:
    """Prepare documents for vector database
    
    Returns:
        tuple: (ids, documents, metadatas)
    """
    ids = []
    documents = []
    metadatas = []
    
    for rule in rules:
        doc_id = rule['id']
        # Combine title and content for better embeddings
        full_text = f"{rule['title']}. {rule['content']}"
        
        ids.append(doc_id)
        documents.append(full_text)
        metadatas.append({
            'section': rule['section'],
            'type': rule['type'],
            'keywords': ', '.join(rule.get('keywords', [])),
            'title': rule['title']
        })
    
    return ids, documents, metadatas

def create_vector_db():
    """Create and populate Chroma vector database"""
    
    if not CHROMA_AVAILABLE:
        print("❌ chromadb is not installed")
        print("   Install with: pip install chromadb")
        return None
    
    # Initialize Chroma client
    client = chromadb.Client(Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory="./vector_db/chroma_data",
        anonymized_telemetry=False
    ))
    
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.parent
    data_path = script_dir / 'data' / 'pdd_sample.json'
    
    print("📚 Loading ПДД data...")
    rules = load_pdd_data(str(data_path))
    print(f"✅ Loaded {len(rules)} rules")
    
    print("📝 Preparing documents...")
    ids, documents, metadatas = prepare_documents(rules)
    
    print("🔄 Creating vector database collection...")
    # Delete existing collection if it exists
    try:
        client.delete_collection(name="pdd_rules")
    except:
        pass
    
    # Create new collection
    collection = client.create_collection(
        name="pdd_rules",
        metadata={"hnsw:space": "cosine"}
    )
    
    print("⏳ Adding documents to vector database...")
    # Add documents to collection
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
    
    # Persist the database
    client.persist()
    
    print(f"✅ Vector database created with {len(ids)} documents")
    print(f"📁 Persisted at: ./vector_db/chroma_data")
    
    return collection

def test_search(collection):
    """Test the vector database search"""
    if not collection or not CHROMA_AVAILABLE:
        print("⚠️  Cannot test search - Chroma not available")
        return
    
    test_queries = [
        "Кто уступает на круге?",
        "Какой штраф за красный свет?",
        "Можно ли обгонять здесь?"
    ]
    
    print("\n🧪 Testing search functionality...\n")
    for query in test_queries:
        results = collection.query(
            query_texts=[query],
            n_results=2
        )
        print(f"Query: {query}")
        if results['documents']:
            print(f"Found: {len(results['documents'][0])} results")
        print()

if __name__ == "__main__":
    collection = create_vector_db()
    if collection:
        test_search(collection)
