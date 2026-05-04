"""
Example usage of ChromaDBManager
"""

import tempfile
import shutil
from services.chroma_manager import ChromaDBManager


def main():
    # Create a temporary directory for this example
    temp_dir = tempfile.mkdtemp()
    
    try:
        print("=== ChromaDB Manager Example ===\n")
        
        # Initialize ChromaDB manager
        print("1. Initializing ChromaDB manager...")
        manager = ChromaDBManager(db_path=temp_dir, collection_name="example_tnved")
        print(f"   Collection initialized with {manager.count()} records\n")
        
        # Add some sample ТНВЭД records
        print("2. Adding sample ТНВЭД records...")
        ids = [
            "0901110000",
            "0901120000",
            "0901210000"
        ]
        embeddings = [
            [1.0, 0.0, 0.0],  # Coffee
            [0.0, 1.0, 0.0],  # Tea
            [0.5, 0.5, 0.0]   # Coffee decaf
        ]
        metadatas = [
            {"description": "КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА"},
            {"description": "ЧАЙ ЗЕЛЕНЫЙ"},
            {"description": "КОФЕ НЕЖАРЕНЫЙ ОСВОБОЖДЕННЫЙ ОТ КОФЕИНА"}
        ]
        documents = [
            "кофе нежареный неосвобожденный от кофеин",
            "чай зеленый",
            "кофе нежареный освобожденный от кофеин"
        ]
        
        manager.add_batch(ids, embeddings, metadatas, documents)
        print(f"   Added {len(ids)} records")
        print(f"   Total records in collection: {manager.count()}\n")
        
        # Query for similar records
        print("3. Searching for records similar to 'coffee'...")
        query_embedding = [0.9, 0.1, 0.0]  # Similar to coffee
        results = manager.query(query_embedding, n_results=2)
        
        print(f"   Found {len(results['ids'][0])} results:")
        for i, code in enumerate(results['ids'][0]):
            distance = results['distances'][0][i]
            metadata = results['metadatas'][0][i]
            print(f"   - Code: {code}")
            print(f"     Description: {metadata['description']}")
            print(f"     Distance: {distance:.4f}\n")
        
        # Convert to SearchResult objects
        print("4. Converting to SearchResult objects...")
        search_results = manager.to_search_results(results)
        for result in search_results:
            print(f"   - {result.code}: {result.description}")
            print(f"     Similarity: {result.similarity_score:.4f}\n")
        
        # Get specific record by code
        print("5. Retrieving specific record by code...")
        record = manager.get_by_code("0901110000")
        if record:
            print(f"   Code: {record['id']}")
            print(f"   Description: {record['metadata']['description']}")
            print(f"   Document: {record['document']}\n")
        
        # Test upsert functionality
        print("6. Testing upsert (updating existing record)...")
        print(f"   Current count: {manager.count()}")
        
        # Update the first record
        manager.add_batch(
            ids=["0901110000"],
            embeddings=[[1.0, 0.0, 0.0]],
            metadatas=[{"description": "КОФЕ НЕЖАРЕНЫЙ (ОБНОВЛЕНО)"}],
            documents=["кофе нежареный обновлено"]
        )
        
        print(f"   Count after upsert: {manager.count()} (should be same)")
        
        # Verify update
        updated_record = manager.get_by_code("0901110000")
        if updated_record:
            print(f"   Updated description: {updated_record['metadata']['description']}\n")
        
        print("=== Example completed successfully! ===")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("\nTemporary directory cleaned up.")


if __name__ == "__main__":
    main()
