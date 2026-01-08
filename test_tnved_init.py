#!/usr/bin/env python3
"""
Test TNVED initialization to isolate recursion issue.
"""

import sys
import traceback

# Set recursion limit to catch errors earlier
sys.setrecursionlimit(200)

def test_tnved_integration():
    """Test TNVED integration initialization."""
    print("🔍 Testing TNVED integration initialization...")
    
    try:
        from batch_processor.services.tnved_integration import get_tnved_integration
        
        print("✅ Import successful")
        
        # Try to get integration
        integration = get_tnved_integration()
        print("✅ Integration created")
        
        # Try to initialize
        integration.initialize()
        print("✅ Integration initialized")
        
        return True
        
    except RecursionError as e:
        print(f"\n🚨 RECURSION ERROR in TNVED integration!")
        print(f"Error: {e}")
        print("\n📋 Full traceback:")
        traceback.print_exc()
        
        # Analyze call stack
        print("\n📊 Call stack analysis:")
        tb = traceback.extract_tb(e.__traceback__)
        call_counts = {}
        
        for frame in tb:
            key = f"{frame.filename.split('/')[-1]}:{frame.name}:{frame.lineno}"
            call_counts[key] = call_counts.get(key, 0) + 1
        
        print("Most frequent calls:")
        for call, count in sorted(call_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            if count > 1:
                print(f"  {call}: {count} times")
        
        return False
        
    except Exception as e:
        print(f"❌ Other error: {e}")
        traceback.print_exc()
        return False

def test_chroma_manager():
    """Test ChromaDB manager initialization."""
    print("\n🔍 Testing ChromaDB manager initialization...")
    
    try:
        from services.chroma_manager import ChromaDBManager
        
        print("✅ Import successful")
        
        # Try to create manager
        manager = ChromaDBManager("./chroma_db", "test_collection")
        print("✅ ChromaDB manager created")
        
        return True
        
    except RecursionError as e:
        print(f"\n🚨 RECURSION ERROR in ChromaDB manager!")
        print(f"Error: {e}")
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"❌ Other error: {e}")
        traceback.print_exc()
        return False

def test_text_normalizer():
    """Test text normalizer initialization."""
    print("\n🔍 Testing text normalizer initialization...")
    
    try:
        from services.text_normalizer import TextNormalizer
        
        print("✅ Import successful")
        
        # Try to create normalizer
        normalizer = TextNormalizer()
        print("✅ Text normalizer created")
        
        # Try to normalize text
        result = normalizer.normalize("test text")
        print(f"✅ Text normalization works: '{result}'")
        
        return True
        
    except RecursionError as e:
        print(f"\n🚨 RECURSION ERROR in text normalizer!")
        print(f"Error: {e}")
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"❌ Other error: {e}")
        traceback.print_exc()
        return False

def test_embedding_generator():
    """Test embedding generator initialization."""
    print("\n🔍 Testing embedding generator initialization...")
    
    try:
        from services.embedding_generator import EmbeddingGenerator
        
        print("✅ Import successful")
        
        # Try to create generator (this might take time)
        generator = EmbeddingGenerator(
            model_name='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
            device='cpu'
        )
        print("✅ Embedding generator created")
        
        return True
        
    except RecursionError as e:
        print(f"\n🚨 RECURSION ERROR in embedding generator!")
        print(f"Error: {e}")
        traceback.print_exc()
        return False
        
    except Exception as e:
        print(f"❌ Other error: {e}")
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("🐛 TNVED Initialization Debug")
    print("=" * 50)
    
    tests = [
        ("Text Normalizer", test_text_normalizer),
        ("ChromaDB Manager", test_chroma_manager),
        ("Embedding Generator", test_embedding_generator),
        ("TNVED Integration", test_tnved_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}:")
        if test_func():
            passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
            # Stop on first failure to isolate the issue
            break
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All TNVED components initialized successfully!")
        return 0
    else:
        print("⚠️  TNVED initialization has recursion issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())