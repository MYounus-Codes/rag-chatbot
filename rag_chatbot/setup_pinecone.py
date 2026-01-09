"""
Pinecone Database Setup Script
==============================
Initializes Pinecone index and upserts product data with embeddings.
Uses HuggingFace sentence-transformers (free, local).
Run this once to set up the vector database.
"""

import os
import json
import time
from glob import glob
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
import fitz  # PyMuPDF

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "support-rag-workflow-chatbot")

# Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)

# Initialize HuggingFace embedding model (free, local)
print("Loading embedding model (all-mpnet-base-v2)...")
embedding_model = SentenceTransformer('all-mpnet-base-v2')
print("Embedding model loaded successfully!")


def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF file using PyMuPDF (fitz) with robust error handling."""
    texts = []
    try:
        # Open with error tolerance
        doc = fitz.open(pdf_path)
        
        for i in range(len(doc)):
            try:
                page = doc[i]
                # Try to get text with error handling
                try:
                    page_text = page.get_text()
                except Exception as page_error:
                    print(f"  ⚠️ Warning: Could not extract text from page {i+1} of {os.path.basename(pdf_path)}: {page_error}")
                    continue
                
                if page_text and page_text.strip():
                    texts.append((i, page_text))
            except Exception as e:
                print(f"  ⚠️ Warning: Error processing page {i+1} of {os.path.basename(pdf_path)}: {e}")
                continue
        
        doc.close()
        
    except Exception as e:
        print(f"  ❌ Error opening {os.path.basename(pdf_path)}: {e}")
    
    return texts


def extract_text_from_txt(txt_path):
    """Extract text from a .txt file, split into chunks if needed."""
    chunks = []
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read()
            # Split into 2000-character chunks
            for i in range(0, len(text), 2000):
                chunk = text[i:i+2000]
                if chunk.strip():
                    chunks.append((i//2000, chunk))
    except Exception as e:
        print(f"  ❌ Error reading {os.path.basename(txt_path)}: {e}")
    return chunks


def load_folder_products():
    """Load product data from all PDFs and TXT files in product_1 and product_2 folders."""
    files = glob("product_1/*") + glob("product_2/*")
    products = []
    
    print(f"\n📂 Found {len(files)} files to process\n")
    
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        base = os.path.basename(file)
        
        print(f"Processing: {base}")
        
        if ext == ".pdf":
            page_texts = extract_text_from_pdf(file)
            
            if not page_texts:
                print(f"  ⚠️ No text extracted from {base}, skipping...\n")
                continue
            
            print(f"  ✓ Extracted {len(page_texts)} pages")
            
            for page_num, page_text in page_texts:
                # Split page_text into 2000-character chunks
                chunk_count = 0
                for i in range(0, len(page_text), 2000):
                    chunk = page_text[i:i+2000]
                    if chunk.strip():
                        products.append({
                            "product_name": f"{base} (page {page_num+1}, chunk {chunk_count+1})",
                            "description": chunk,
                            "manufacturer_website": ""
                        })
                        chunk_count += 1
                
                print(f"  ✓ Page {page_num+1}: Created {chunk_count} chunks")
            
            print()
            
        elif ext == ".txt":
            chunks = extract_text_from_txt(file)
            
            if not chunks:
                print(f"  ⚠️ No text extracted from {base}, skipping...\n")
                continue
            
            print(f"  ✓ Extracted {len(chunks)} chunks")
            
            for chunk_num, chunk in chunks:
                products.append({
                    "product_name": f"{base} (chunk {chunk_num+1})",
                    "description": chunk,
                    "manufacturer_website": ""
                })
            
            print()
    
    return products


def get_embedding(text: str) -> list:
    """Generate embedding using HuggingFace sentence-transformers."""
    embedding = embedding_model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def load_product_data(filepath: str = "db_data.json") -> list:
    """Load product data from JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def create_index():
    """Create Pinecone index if it doesn't exist."""
    existing_indexes = [index.name for index in pc.list_indexes()]
    
    if PINECONE_INDEX_NAME in existing_indexes:
        print(f"Index '{PINECONE_INDEX_NAME}' already exists.")
        return
    
    print(f"Creating index '{PINECONE_INDEX_NAME}'...")
    
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=768,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )
    
    while not pc.describe_index(PINECONE_INDEX_NAME).status["ready"]:
        print("Waiting for index to be ready...")
        time.sleep(5)
    
    print(f"Index '{PINECONE_INDEX_NAME}' created successfully!")


def delete_all_vectors():
    """Delete all vectors from the Pinecone index."""
    index = pc.Index(PINECONE_INDEX_NAME)
    print(f"Deleting all vectors from index '{PINECONE_INDEX_NAME}'...")
    stats = index.describe_index_stats()
    if stats.total_vector_count == 0:
        print("Index is already empty.")
        return
    index.delete(delete_all=True)
    print("All vectors deleted.")


def upsert_products():
    """Generate embeddings and upsert product data to Pinecone."""
    products = load_folder_products()
    
    if not products:
        print("❌ No products loaded! Check your PDF/TXT files.")
        return
    
    index = pc.Index(PINECONE_INDEX_NAME)
    
    print(f"\n{'='*50}")
    print(f"Processing {len(products)} product chunks for embedding...")
    print(f"{'='*50}\n")
    
    vectors = []
    for i, product in enumerate(products):
        combined_text = f"{product['product_name']}: {product['description']}"
        
        print(f"[{i+1}/{len(products)}] {product['product_name'][:60]}...")
        
        embedding = get_embedding(combined_text)
        
        vector = {
            "id": f"product_{i}",
            "values": embedding,
            "metadata": {
                "product_name": product["product_name"],
                "description": product["description"],
                "manufacturer_website": product.get("manufacturer_website", ""),
            }
        }
        vectors.append(vector)
        
        # Batch upsert every 10 vectors
        if len(vectors) >= 10:
            index.upsert(vectors=vectors)
            print(f"  ✓ Upserted batch of {len(vectors)} vectors\n")
            vectors = []
            time.sleep(0.5)
    
    # Upsert remaining vectors
    if vectors:
        index.upsert(vectors=vectors)
        print(f"  ✓ Upserted final batch of {len(vectors)} vectors\n")
    
    print(f"{'='*50}")
    print(f"✅ Successfully upserted all products to Pinecone!")
    print(f"{'='*50}\n")
    
    stats = index.describe_index_stats()
    print(f"Index Stats:")
    print(f"  Total vectors: {stats.total_vector_count}")


def test_search():
    """Test the search functionality."""
    index = pc.Index(PINECONE_INDEX_NAME)
    
    test_queries = [
        "installation instructions",
        "troubleshooting guide",
        "technical specifications",
        "warranty information",
    ]
    
    print("\n" + "="*50)
    print("Testing Search Functionality")
    print("="*50)
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        
        embedding = get_embedding(query)
        results = index.query(vector=embedding, top_k=3, include_metadata=True)
        
        print("   Results:")
        for match in results.matches:
            print(f"   - {match.metadata['product_name'][:70]}... (score: {match.score:.3f})")


def main():
    """Main function to set up Pinecone database."""
    print("="*50)
    print("Pinecone Database Setup")
    print("="*50)
    print()
    
    if not PINECONE_API_KEY:
        print("❌ Error: PINECONE_API_KEY not set")
        return
    
    print(f"📌 Index Name: {PINECONE_INDEX_NAME}")
    print(f"🔑 Pinecone API Key: {PINECONE_API_KEY[:10]}...")
    print(f"🤖 Embedding Model: all-mpnet-base-v2 (768 dimensions)")
    print()
    
    # Step 1: Create index
    create_index()

    # Step 2: Delete all previous vectors
    delete_all_vectors()

    # Step 3: Upsert products
    upsert_products()

    # Step 4: Test search
    test_search()
    
    print("\n" + "="*50)
    print("✅ Setup Complete!")
    print("="*50)


if __name__ == "__main__":
    main()