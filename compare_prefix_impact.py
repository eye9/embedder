#!/usr/bin/env python3
"""
Script to demonstrate the impact of using FRIDA prefixes on search quality.

This script compares embeddings and similarity scores with and without prefixes
to show how prefixes improve semantic matching.
"""

import numpy as np
from services.embedding_generator import EmbeddingGenerator
from services.text_normalizer import TextNormalizer


def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def main():
    print("=" * 80)
    print("FRIDA Prefix Impact Demonstration")
    print("=" * 80)
    print()
    
    # Initialize components
    print("Initializing components...")
    generator = EmbeddingGenerator(model_name="ai-forever/FRIDA", device="cpu")
    normalizer = TextNormalizer()
    print("✓ Components initialized")
    print()
    
    # Test cases: query and relevant/irrelevant documents
    test_cases = [
        {
            "query": "кофейные зерна арабика",
            "relevant_doc": "кофе арабика в зернах",
            "irrelevant_doc": "чай черный байховый"
        },
        {
            "query": "сахар белый",
            "relevant_doc": "сахар белый кристаллический",
            "irrelevant_doc": "соль морская пищевая"
        },
        {
            "query": "зеленый чай",
            "relevant_doc": "чай зеленый листовой",
            "irrelevant_doc": "кофе растворимый"
        }
    ]
    
    print("Testing search quality with and without prefixes...")
    print("=" * 80)
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        relevant_doc = test_case["relevant_doc"]
        irrelevant_doc = test_case["irrelevant_doc"]
        
        # Normalize texts
        query_norm = normalizer.normalize(query)
        relevant_norm = normalizer.normalize(relevant_doc)
        irrelevant_norm = normalizer.normalize(irrelevant_doc)
        
        print(f"Test Case {i}:")
        print(f"  Query:         {query}")
        print(f"  Relevant Doc:  {relevant_doc}")
        print(f"  Irrelevant Doc: {irrelevant_doc}")
        print()
        
        # WITHOUT PREFIXES
        print("  WITHOUT PREFIXES:")
        query_emb_no_prefix = generator.generate(query_norm)
        relevant_emb_no_prefix = generator.generate(relevant_norm)
        irrelevant_emb_no_prefix = generator.generate(irrelevant_norm)
        
        sim_relevant_no_prefix = cosine_similarity(query_emb_no_prefix, relevant_emb_no_prefix)
        sim_irrelevant_no_prefix = cosine_similarity(query_emb_no_prefix, irrelevant_emb_no_prefix)
        margin_no_prefix = sim_relevant_no_prefix - sim_irrelevant_no_prefix
        
        print(f"    Relevant similarity:   {sim_relevant_no_prefix:.4f}")
        print(f"    Irrelevant similarity: {sim_irrelevant_no_prefix:.4f}")
        print(f"    Margin:                {margin_no_prefix:.4f}")
        print()
        
        # WITH PREFIXES
        print("  WITH PREFIXES:")
        query_emb_with_prefix = generator.generate(query_norm, prefix="search_query: ")
        relevant_emb_with_prefix = generator.generate(relevant_norm, prefix="search_document: ")
        irrelevant_emb_with_prefix = generator.generate(irrelevant_norm, prefix="search_document: ")
        
        sim_relevant_with_prefix = cosine_similarity(query_emb_with_prefix, relevant_emb_with_prefix)
        sim_irrelevant_with_prefix = cosine_similarity(query_emb_with_prefix, irrelevant_emb_with_prefix)
        margin_with_prefix = sim_relevant_with_prefix - sim_irrelevant_with_prefix
        
        print(f"    Relevant similarity:   {sim_relevant_with_prefix:.4f}")
        print(f"    Irrelevant similarity: {sim_irrelevant_with_prefix:.4f}")
        print(f"    Margin:                {margin_with_prefix:.4f}")
        print()
        
        # COMPARISON
        margin_improvement = margin_with_prefix - margin_no_prefix
        improvement_pct = (margin_improvement / abs(margin_no_prefix)) * 100 if margin_no_prefix != 0 else 0
        
        print(f"  IMPROVEMENT:")
        print(f"    Margin increase:       {margin_improvement:+.4f}")
        print(f"    Improvement:           {improvement_pct:+.1f}%")
        
        if margin_with_prefix > margin_no_prefix:
            print(f"    Result:                ✓ Better separation with prefixes")
        else:
            print(f"    Result:                ✗ No improvement")
        
        print()
        print("-" * 80)
        print()
    
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print()
    print("Using proper prefixes (search_query: and search_document:) helps the FRIDA")
    print("model better distinguish between relevant and irrelevant documents by:")
    print()
    print("  1. Optimizing query embeddings for matching against documents")
    print("  2. Optimizing document embeddings for being retrieved")
    print("  3. Increasing the similarity margin between relevant and irrelevant results")
    print()
    print("This leads to:")
    print("  • More accurate search results")
    print("  • Better ranking of relevant documents")
    print("  • Improved user experience")
    print()
    print("Recommendation: Always use prefixes when working with FRIDA model!")
    print()


if __name__ == "__main__":
    main()
