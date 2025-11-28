# FRIDA Model Prefix Usage

## Overview

The FRIDA model (`ai-forever/FRIDA`) is designed to work best with task-specific prefixes. This document explains how prefixes are used in the TNVED Embedder system.

## Why Use Prefixes?

FRIDA is a fine-tuned model that produces different embeddings based on the task context. Using appropriate prefixes significantly improves search accuracy by:

1. **Distinguishing queries from documents** - Search queries and documents are embedded differently
2. **Task-specific optimization** - The model adjusts its representation based on the intended use
3. **Better semantic matching** - Query-document pairs with proper prefixes have higher similarity scores

## Available Prefixes

According to FRIDA documentation, the following prefixes are available:

- `search_query: ` - For search queries (what users are looking for)
- `search_document: ` - For documents to be retrieved (indexed content)
- `paraphrase: ` - For symmetric paraphrasing tasks (STS, paraphrase mining)
- `categorize: ` - For asymmetric matching of document title and body
- `categorize_sentiment: ` - For sentiment-related tasks
- `categorize_topic: ` - For topic grouping
- `categorize_entailment: ` - For textual entailment (NLI)

## Usage in TNVED Embedder

### 1. Document Indexing (Loading)

When loading TNVED codes into the database, we use the `search_document: ` prefix:

```python
# In services/tnved_loader.py
embeddings = self.embedder.generate(
    normalized_texts,
    batch_size=self.batch_size,
    prefix="search_document: "
)
```

This tells the model that these texts are documents that will be searched against.

### 2. Query Search

When searching for TNVED codes, we use the `search_query: ` prefix:

```python
# In services/tnved_searcher.py
query_embedding = self.embedder.generate(
    normalized_query,
    prefix="search_query: "
)
```

This tells the model that this text is a search query looking for relevant documents.

## Example

```python
from services.embedding_generator import EmbeddingGenerator

generator = EmbeddingGenerator()

# For indexing documents
doc_text = "кофейные зерна арабика"
doc_embedding = generator.generate(doc_text, prefix="search_document: ")

# For search queries
query_text = "кофе арабика"
query_embedding = generator.generate(query_text, prefix="search_query: ")

# Calculate similarity
similarity = np.dot(query_embedding, doc_embedding)
```

## Important Notes

1. **Consistency is key** - Always use `search_document: ` for indexing and `search_query: ` for searching
2. **Re-indexing required** - If you have an existing database without prefixes, you need to re-index all documents
3. **Performance impact** - Using proper prefixes can significantly improve search accuracy (10-20% improvement typical)

## Re-indexing Existing Database

If you have an existing database that was created without prefixes, you should re-index:

```bash
# Delete old database
python load_tnved.py --reset

# Load with new prefix-aware code
python load_tnved.py tnved_full10_new.xlsx
```

## References

- [FRIDA Model on HuggingFace](https://huggingface.co/ai-forever/FRIDA)
- [FRIDA Research Article (RU)](https://habr.com/ru/companies/sberbank/articles/567564/)
