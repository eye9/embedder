"""
Example script demonstrating EmbeddingGenerator usage.
"""

from services.embedding_generator import EmbeddingGenerator
from services.text_normalizer import TextNormalizer


def main():
    """Demonstrate embedding generation with FRIDA model."""
    print("Initializing EmbeddingGenerator with FRIDA model...")
    generator = EmbeddingGenerator(model_name="ai-forever/FRIDA", device="cpu")
    
    print(f"Model loaded: {generator}")
    print(f"Embedding dimension: {generator.get_embedding_dimension()}")
    print()
    
    # Initialize text normalizer
    normalizer = TextNormalizer()
    
    # Example texts
    texts = [
        "КОФЕЙНЫЕ ЗЕРНА АРАБИКА",
        "Чай черный байховый",
        "Сахар белый кристаллический"
    ]
    
    print("Generating embeddings for sample texts (with search_document prefix):")
    print("-" * 60)
    
    for text in texts:
        # Normalize text
        normalized = normalizer.normalize(text)
        
        # Generate embedding with search_document prefix (for indexing)
        embedding = generator.generate(normalized, prefix="search_document: ")
        
        print(f"Original:    {text}")
        print(f"Normalized:  {normalized}")
        print(f"Embedding:   shape={embedding.shape}, dtype={embedding.dtype}")
        print(f"First 5 values: {embedding[:5]}")
        print()
    
    # Batch processing example
    print("Batch processing example (with search_document prefix):")
    print("-" * 60)
    normalized_texts = [normalizer.normalize(t) for t in texts]
    batch_embeddings = generator.generate(
        normalized_texts,
        batch_size=2,
        prefix="search_document: "
    )
    print(f"Generated {batch_embeddings.shape[0]} embeddings")
    print(f"Embedding shape: {batch_embeddings.shape}")
    print()
    
    # Determinism test
    print("Testing determinism (same input should produce same output):")
    print("-" * 60)
    text = "кофе"
    emb1 = generator.generate(text, prefix="search_query: ")
    emb2 = generator.generate(text, prefix="search_query: ")
    are_equal = (emb1 == emb2).all()
    print(f"Text: {text}")
    print(f"Embeddings are identical: {are_equal}")
    print()
    
    # Prefix comparison
    print("Comparing embeddings with different prefixes:")
    print("-" * 60)
    query_text = "кофейные зерна"
    emb_no_prefix = generator.generate(query_text)
    emb_query = generator.generate(query_text, prefix="search_query: ")
    emb_doc = generator.generate(query_text, prefix="search_document: ")
    
    print(f"Text: {query_text}")
    print(f"No prefix:        {emb_no_prefix[:5]}")
    print(f"search_query:     {emb_query[:5]}")
    print(f"search_document:  {emb_doc[:5]}")
    print()
    print("Note: FRIDA model produces different embeddings based on the prefix,")
    print("which helps improve search accuracy by distinguishing queries from documents.")
    print()


if __name__ == "__main__":
    main()

