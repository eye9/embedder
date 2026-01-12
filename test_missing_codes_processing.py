#!/usr/bin/env python3
"""
Test TNVED code matching for missing codes in GUOO-Manifest file
"""

import sys
import pandas as pd
from pathlib import Path

# Add project root to path
sys.path.insert(0, '.')

def test_missing_codes():
    """Test TNVED code matching for records with missing codes"""
    
    print("🔍 Testing TNVED code matching for missing codes...")
    
    try:
        # Import required services
        from services.chroma_manager import ChromaDBManager
        from services.tnved_selector import TNVEDSelector
        from services.url_matcher import URLMatcher
        from services.url_database_manager import URLDatabaseManager
        from services.url_processor_factory import URLProcessorFactory
        
        print("✅ Imports successful")
        
        # Initialize services
        chroma_manager = ChromaDBManager()
        tnved_selector = TNVEDSelector(chroma_manager)
        
        # Initialize URL processing if available
        try:
            url_components = URLProcessorFactory.create_complete_url_processor()
            url_matcher = url_components.get("matcher")
            print("✅ URL processing available")
        except Exception as e:
            print(f"⚠️ URL processing not available: {e}")
            url_matcher = None
        
        # Read test file
        test_file = "test_missing_codes.xlsx"
        if not Path(test_file).exists():
            print(f"❌ Test file not found: {test_file}")
            return False
        
        df = pd.read_excel(test_file)
        print(f"📄 Processing {len(df)} records with missing codes")
        
        results = []
        
        for idx, row in df.iterrows():
            print(f"\n--- Record {idx + 1} ---")
            description = row['Description']
            description_en = row['Description_EN']
            url = row.get('URL', '')
            original_row = row['Original_Row']
            
            print(f"Description: {description}")
            print(f"Description EN: {description_en}")
            print(f"URL: {url}")
            
            # Try URL matching first if available
            url_match = None
            if url_matcher and url and pd.notna(url) and url.strip():
                try:
                    url_result = url_matcher.find_tnved_code(url.strip())
                    if url_result and url_result.tnved_code:
                        url_match = url_result.tnved_code
                        print(f"🔗 URL match found: {url_match}")
                except Exception as e:
                    print(f"⚠️ URL matching failed: {e}")
            
            # Use semantic search if no URL match
            if not url_match:
                try:
                    # Try English description first, then Russian
                    search_text = description_en if description_en and pd.notna(description_en) else description
                    
                    results_list = tnved_selector.find_similar_codes(search_text, top_k=3)
                    
                    if results_list:
                        best_match = results_list[0]
                        print(f"🎯 Semantic match: {best_match['code']} (similarity: {best_match['similarity']:.3f})")
                        print(f"   Description: {best_match['description']}")
                        
                        # Show alternatives
                        if len(results_list) > 1:
                            print("   Alternatives:")
                            for i, alt in enumerate(results_list[1:], 2):
                                print(f"   {i}. {alt['code']} (similarity: {alt['similarity']:.3f})")
                        
                        results.append({
                            'Original_Row': original_row,
                            'Description': description,
                            'URL': url,
                            'Suggested_Code': best_match['code'],
                            'Similarity': best_match['similarity'],
                            'Match_Type': 'URL' if url_match else 'Semantic',
                            'TNVED_Description': best_match['description']
                        })
                    else:
                        print("❌ No matches found")
                        results.append({
                            'Original_Row': original_row,
                            'Description': description,
                            'URL': url,
                            'Suggested_Code': 'NO_MATCH',
                            'Similarity': 0.0,
                            'Match_Type': 'None',
                            'TNVED_Description': ''
                        })
                        
                except Exception as e:
                    print(f"❌ Semantic search failed: {e}")
                    results.append({
                        'Original_Row': original_row,
                        'Description': description,
                        'URL': url,
                        'Suggested_Code': 'ERROR',
                        'Similarity': 0.0,
                        'Match_Type': 'Error',
                        'TNVED_Description': str(e)
                    })
            else:
                results.append({
                    'Original_Row': original_row,
                    'Description': description,
                    'URL': url,
                    'Suggested_Code': url_match,
                    'Similarity': 1.0,
                    'Match_Type': 'URL',
                    'TNVED_Description': 'URL match'
                })
        
        # Save results
        results_df = pd.DataFrame(results)
        output_file = "missing_codes_results.xlsx"
        results_df.to_excel(output_file, index=False)
        
        print(f"\n✅ Processing completed! Results saved to: {output_file}")
        print("\n📊 Summary:")
        print(results_df[['Original_Row', 'Suggested_Code', 'Similarity', 'Match_Type']].to_string())
        
        return True
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_missing_codes()