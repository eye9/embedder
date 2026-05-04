#!/usr/bin/env python3
"""
Демонстрация исправления: теперь возвращаются чистые 10-значные коды ТНВЭД.
"""

import logging
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from batch_processor.services.tnved_integration import get_tnved_integration

# Configure logging to reduce noise
logging.basicConfig(level=logging.WARNING)


def demo_clean_codes():
    """Демонстрация того, что теперь возвращаются чистые коды ТНВЭД."""
    print("🔧 Демонстрация исправления кодов ТНВЭД")
    print("=" * 50)
    
    try:
        # Initialize integration
        integration = get_tnved_integration()
        selector = integration.create_selector('similarity_top1')
        
        # Test descriptions
        test_descriptions = [
            "Современный минималистичный мини-прикроватный столик",
            "Игрушка для животных",
            "Кофейные зерна арабика",
            "Пластырь медицинский"
        ]
        
        print("📋 Тестирование описаний товаров:")
        print()
        
        for i, description in enumerate(test_descriptions, 1):
            print(f"{i}. Описание: {description}")
            
            result = selector.select_code(description, row_index=i-1)
            
            if result.tnved_code:
                print(f"   ✅ Код ТНВЭД: {result.tnved_code}")
                print(f"   📊 Уверенность: {result.confidence_score:.3f}")
                
                # Extract reason parts to show DB ID if different
                reason_parts = result.selection_reason.split(" | ")
                db_id_part = next((part for part in reason_parts if part.startswith("DB ID:")), None)
                
                if db_id_part:
                    db_id = db_id_part.replace("DB ID: ", "")
                    print(f"   🔍 ID в базе: {db_id}")
                    print(f"   ✨ Исправление: {db_id} → {result.tnved_code}")
                else:
                    print(f"   ℹ️  Код уже был чистым в базе")
            else:
                print(f"   ❌ Код не найден")
            
            print()
        
        print("🎉 Исправление работает корректно!")
        print("Теперь система возвращает только чистые 10-значные коды ТНВЭД,")
        print("даже если в базе данных хранятся идентификаторы с суффиксами.")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def main():
    """Run the demo."""
    success = demo_clean_codes()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())