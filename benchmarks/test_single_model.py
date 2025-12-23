"""
Быстрый тест одной модели эмбеддингов.

Используйте этот скрипт для быстрой проверки модели перед полным сравнением.
"""

import sys
import os
import time
import yaml
import torch

# Добавить корневую директорию проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.embedding_generator import EmbeddingGenerator
from services.text_normalizer import TextNormalizer
from services.tnved_searcher import TNVEDSearcher


def test_model(model_name: str, device: str = "cpu"):
    """Быстрый тест модели."""
    print(f"\n{'='*80}")
    print(f"ТЕСТ МОДЕЛИ: {model_name}")
    print(f"Устройство: {device.upper()}")
    print(f"{'='*80}\n")
    
    # Загрузка конфигурации
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Проверка CUDA
    if device == "cuda":
        if not torch.cuda.is_available():
            print("⚠️  CUDA недоступна, используется CPU")
            device = "cpu"
        else:
            print(f"✓ GPU: {torch.cuda.get_device_name(0)}")
            print(f"✓ CUDA память: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB\n")
    
    # Загрузка модели
    print("Загрузка модели...")
    start = time.time()
    try:
        embedder = EmbeddingGenerator(model_name=model_name, device=device)
        load_time = time.time() - start
        print(f"✓ Модель загружена за {load_time:.2f}с")
        print(f"✓ Размерность эмбеддингов: {embedder.get_embedding_dimension()}\n")
    except Exception as e:
        print(f"✗ Ошибка загрузки модели: {e}")
        return
    
    # Тест генерации эмбеддингов
    print("Тест генерации эмбеддингов...")
    test_texts = [
        "кофе в зернах",
        "свежие яблоки",
        "пшеничная мука"
    ]
    
    start = time.time()
    embeddings = embedder.generate(test_texts)
    gen_time = time.time() - start
    
    print(f"✓ Сгенерировано {len(test_texts)} эмбеддингов за {gen_time:.3f}с")
    print(f"✓ Скорость: {len(test_texts)/gen_time:.2f} эмбеддингов/сек\n")
    
    # Тест поиска
    print("Тест поиска...")
    normalizer = TextNormalizer()
    
    try:
        searcher = TNVEDSearcher(
            db_path=config["database"]["path"],
            normalizer=normalizer,
            embedder=embedder,
            collection_name=config["database"]["collection_name"]
        )
        
        test_query = "кофе в зернах арабика"
        print(f"Запрос: '{test_query}'")
        
        start = time.time()
        results = searcher.search(test_query, top_k=5)
        search_time = time.time() - start
        
        print(f"✓ Поиск выполнен за {search_time:.3f}с")
        print(f"✓ Найдено результатов: {len(results)}\n")
        
        # Вывод результатов
        print("Топ-5 результатов:")
        print("-" * 80)
        for i, result in enumerate(results, 1):
            desc = result.description[:60] + "..." if len(result.description) > 60 else result.description
            print(f"{i}. {result.code}")
            print(f"   {desc}")
            print(f"   Score: {result.similarity_score:.4f}\n")
            
    except Exception as e:
        search_time = 0
        results = []
        print(f"⚠️  Ошибка поиска: {e}")
        
        # Проверка на ошибку размерности
        if "dimension" in str(e).lower():
            print("\n⚠️  НЕСОВМЕСТИМОСТЬ РАЗМЕРНОСТИ ЭМБЕДДИНГОВ")
            print(f"   База данных создана с другой моделью")
            print(f"   Модель {model_name} создает эмбеддинги размерности {embedder.get_embedding_dimension()}")
            print("\n   Для тестирования поиска:")
            print("   1. Обновите config.yaml:")
            print(f"      model:")
            print(f"        name: \"{model_name}\"")
            print("   2. Пересоздайте базу данных:")
            print("      python load_tnved.py tnved_full10_new.xlsx --reset")
            print("   3. Повторите тест")
        print()
    
    # Итоги
    print("="*80)
    print("ИТОГИ")
    print("="*80)
    print(f"Модель: {model_name}")
    print(f"Устройство: {device}")
    print(f"Загрузка: {load_time:.2f}с")
    print(f"Генерация: {len(test_texts)/gen_time:.2f} эмбеддингов/сек")
    print(f"Поиск: {search_time:.3f}с")
    
    if results:
        avg_score = sum(r.similarity_score for r in results) / len(results)
        print(f"Средний score: {avg_score:.4f}")
    else:
        print("Средний score: N/A (нет результатов)")
        print("\n⚠️  База данных пуста или несовместима с этой моделью")
        print("⚠️  Для тестирования поиска:")
        print("   1. Обновите config.yaml с этой моделью")
        print("   2. Загрузите данные: python load_tnved.py tnved_full10_new.xlsx")
        print("   3. Повторите тест")
    
    print("="*80)


def main():
    """Главная функция."""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python test_single_model.py <model_name> [device]")
        print("\nПримеры:")
        print("  python test_single_model.py intfloat/multilingual-e5-small")
        print("  python test_single_model.py intfloat/multilingual-e5-small cuda")
        print("  python test_single_model.py cointegrated/rubert-tiny2 cpu")
        print("\nДоступные модели:")
        print("  • ai-forever/FRIDA")
        print("  • intfloat/multilingual-e5-small")
        print("  • sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        print("  • cointegrated/rubert-tiny2")
        sys.exit(1)
    
    model_name = sys.argv[1]
    device = sys.argv[2] if len(sys.argv) > 2 else "cpu"
    
    test_model(model_name, device)


if __name__ == "__main__":
    main()
