"""
Example usage of TNVEDSearcher

This script demonstrates how to search for ТНВЭД codes using text descriptions.
"""

import logging
from services import TextNormalizer, EmbeddingGenerator, TNVEDSearcher


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def main():
    print("=== ТНВЭД Searcher Example ===\n")
    
    # Initialize components
    print("1. Initializing components...")
    normalizer = TextNormalizer()
    embedder = EmbeddingGenerator(model_name="ai-forever/FRIDA", device="cpu")
    
    # Initialize searcher (assumes data has been loaded)
    db_path = "./chroma_db"
    searcher = TNVEDSearcher(
        db_path=db_path,
        normalizer=normalizer,
        embedder=embedder,
        collection_name="tnved"
    )
    
    # Get database statistics
    stats = searcher.get_database_stats()
    print(f"   Database contains {stats['total_records']} ТНВЭД codes\n")
    
    if stats['total_records'] == 0:
        print("⚠️  Database is empty. Please load data first using example_loader.py")
        return
    
    # Example searches
    queries = [
        "кофейные зерна арабика",
        "зеленый чай",
        "сахар белый кристаллический",
        "пшеничная мука высшего сорта",
        "молоко коровье пастеризованное"
    ]
    
    print("2. Performing example searches...\n")
    
    for i, query in enumerate(queries, 1):
        print(f"   Query {i}: '{query}'")
        print("   " + "-" * 60)
        
        try:
            # Search for top 3 results
            results = searcher.search(query, top_k=3)
            
            if results:
                for j, result in enumerate(results, 1):
                    print(f"   {j}. Code: {result.code}")
                    print(f"      Description: {result.description}")
                    print(f"      Similarity: {result.similarity_score:.4f}")
                    print()
            else:
                print("   No results found\n")
                
        except Exception as e:
            print(f"   Error: {e}\n")
    
    # Test getting specific code details
    print("3. Testing code lookup...\n")
    
    # Get details for a specific code (if it exists)
    test_code = "0901110000"
    print(f"   Looking up code: {test_code}")
    
    try:
        result = searcher.get_code_details(test_code)
        
        if result:
            print(f"   ✓ Found:")
            print(f"     Code: {result.code}")
            print(f"     Description: {result.description}")
            print(f"     Normalized: {result.normalized_text}")
        else:
            print(f"   ✗ Code not found in database")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n=== Example completed! ===")


if __name__ == "__main__":
    main()
