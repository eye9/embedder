"""
Text normalization service for Russian text processing.

This module provides text normalization functionality using the Natasha library
for Russian text lemmatization, along with lowercase conversion and whitespace cleanup.
"""

import re
import warnings
from typing import Optional

# Suppress pymorphy2 pkg_resources deprecation warning
warnings.filterwarnings('ignore', message='.*pkg_resources is deprecated.*')

from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    Doc
)


class TextNormalizer:
    """
    Normalizes Russian text for consistent processing.
    
    Performs the following operations:
    1. Converts text to lowercase
    2. Lemmatizes Russian words using Natasha
    3. Removes excessive whitespace and special characters
    
    This ensures consistent text representation for embedding generation
    and similarity search.
    """
    
    def __init__(self):
        """Initialize Natasha components for Russian text processing."""
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        
        # Initialize embeddings and tagger for morphological analysis
        self.emb = NewsEmbedding()
        self.morph_tagger = NewsMorphTagger(self.emb)
    
    def normalize(self, text: str) -> str:
        """
        Normalize text through lowercase conversion, lemmatization, and cleanup.
        
        Args:
            text: Input text to normalize
            
        Returns:
            Normalized text with lowercase, lemmatized words, and cleaned whitespace
            
        Examples:
            >>> normalizer = TextNormalizer()
            >>> normalizer.normalize("КОФЕЙНЫЕ ЗЕРНА")
            'кофейный зерно'
            >>> normalizer.normalize("  Много   пробелов  ")
            'много пробел'
        """
        if not text or not text.strip():
            return ""
        
        # Step 1: Convert to lowercase
        text = text.lower()
        
        # Step 2: Lemmatize using Natasha
        text = self._lemmatize(text)
        
        # Step 3: Clean up whitespace and special characters
        text = self._cleanup(text)
        
        return text
    
    def _lemmatize(self, text: str) -> str:
        """
        Lemmatize Russian text using Natasha.
        
        Args:
            text: Lowercase text to lemmatize
            
        Returns:
            Text with words converted to their lemma (base) forms
        """
        # Create a Doc object for processing
        doc = Doc(text)
        
        # Segment into tokens
        doc.segment(self.segmenter)
        
        # Perform morphological tagging
        doc.tag_morph(self.morph_tagger)
        
        # Lemmatize tokens
        for token in doc.tokens:
            token.lemmatize(self.morph_vocab)
        
        # Reconstruct text from lemmas
        lemmas = [token.lemma for token in doc.tokens if token.lemma]
        return " ".join(lemmas)
    
    def _cleanup(self, text: str) -> str:
        """
        Clean up whitespace and special characters.
        
        Args:
            text: Text to clean
            
        Returns:
            Text with normalized whitespace and removed special characters
        """
        # Remove special characters except spaces and alphanumeric
        # Keep Cyrillic letters, Latin letters, digits, and spaces
        text = re.sub(r'[^\w\s]', ' ', text, flags=re.UNICODE)
        
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading and trailing whitespace
        text = text.strip()
        
        return text
