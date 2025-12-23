"""
Детальное сравнение результатов поиска для разных моделей.

Этот скрипт показывает side-by-side сравнение результатов поиска
для одних и тех же запросов с разными моделями эмбеддингов.
"""

import sys
import os
import logging
import yaml
from typing import List, Dict
from tabulate import tabulate

# Добавить корневую директорию проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.embedding_generator import EmbeddingGenerator
from services.text_normalizer import TextNormalizer
from services.tnved_searcher import TNVEDSearcher


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Модели для сравнения (можно выбрать 2-3 для детального анализа)
MODELS = [
    ("FRIDA", "ai-forever/FRIDA"),
    ("E5-Small", "intfloat/multilingual-e5-small"),
    ("RuBERT-Tiny2", "cointegrated/rubert-tiny2")
]


# Тестовые запросы
TEST_QUERIES = [
    "кофе в зернах",
    "свежие яблоки",
    "пшеничная мука",
    "оливковое масло",
    "черный чай"
]


def load_config(config_path: str = None) -> dict:
    """Загрузить конфигурацию."""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def compare_search_results(
    query: str,
    models: List[tuple],
    config: dict,
    top_k: int = 5
):
    """
    Сравнить результаты поиска для одного запроса с разными моделями.
    """
    logger.info(f"\n{'='*100}")
    logger.info(f"ЗАПРОС: '{query}'")
    logger.info(f"{'='*100}\n")
    
    normalizer = TextNormalizer()
    db_path = config["database"]["path"]
    collection_name = config["database"]["collection_name"]
    device = config["model"].get("device", "cpu")
    
    all_results = {}
    
    # Получить результаты для каждой модели
    for model_name, model_id in models:
        logger.info(f"Поиск с моделью: {model_name}...")
        
        try:
            embedder = EmbeddingGenerator(model_name=model_id, device=device)
            searcher = TNVEDSearcher(
                db_path=db_path,
                normalizer=normalizer,
                embedder=embedder,
                collection_name=collection_name
            )
            
            results = searcher.search(query, top_k=top_k)
            all_results[model_name] = results
            
        except Exception as e:
            logger.error(f"Ошибка для модели {model_name}: {e}")
            all_results[model_name] = []
    
    # Вывод результатов в виде таблицы
    print("\n" + "="*100)
    print(f"РЕЗУЛЬТАТЫ ПОИСКА: '{query}'")
    print("="*100 + "\n")
    
    # Создать таблицу для каждой позиции
    for i in range(top_k):
        table_data = []
        
        for model_name in [m[0] for m in models]:
            results = all_results.get(model_name, [])
            
            if i < len(results):
                result = results[i]
                row = [
                    model_name,
                    result.code,
                    result.description[:50] + "..." if len(result.description) > 50 else result.description,
                    f"{result.similarity_score:.4f}"
                ]
            else:
                row = [model_name, "-", "-", "-"]
            
            table_data.append(row)
        
        print(f"\nПозиция {i+1}:")
        print(tabulate(
            table_data,
            headers=["Модель", "Код ТНВЭД", "Описание", "Score"],
            tablefmt="grid"
        ))
    
    # Анализ пересечений
    print("\n" + "-"*100)
    print("АНАЛИЗ ПЕРЕСЕЧЕНИЙ")
    print("-"*100)
    
    # Найти общие коды в топ-5
    model_codes = {}
    for model_name, results in all_results.items():
        model_codes[model_name] = set(r.code for r in results)
    
    if len(model_codes) >= 2:
        model_names = list(model_codes.keys())
        
        # Попарное сравнение
        for i in range(len(model_names)):
            for j in range(i+1, len(model_names)):
                m1, m2 = model_names[i], model_names[j]
                common = model_codes[m1] & model_codes[m2]
                total = model_codes[m1] | model_codes[m2]
                
                overlap_pct = (len(common) / len(total) * 100) if total else 0
                
                print(f"\n{m1} ∩ {m2}:")
                print(f"  Общих кодов: {len(common)}/{top_k}")
                print(f"  Процент пересечения: {overlap_pct:.1f}%")
                if common:
                    print(f"  Общие коды: {', '.join(sorted(common))}")


def main():
    """Главная функция."""
    config = load_config()
    
    print("\n" + "="*100)
    print("ДЕТАЛЬНОЕ СРАВНЕНИЕ РЕЗУЛЬТАТОВ ПОИСКА")
    print("="*100)
    print(f"\nСравниваемые модели:")
    for name, model_id in MODELS:
        print(f"  • {name}: {model_id}")
    print(f"\nТестовых запросов: {len(TEST_QUERIES)}")
    print(f"Топ результатов: 5")
    print("="*100)
    
    # Сравнить результаты для каждого запроса
    for query in TEST_QUERIES:
        compare_search_results(query, MODELS, config, top_k=5)
        print("\n")
    
    # Итоговые выводы
    print("\n" + "="*100)
    print("ВЫВОДЫ")
    print("="*100)
    print("""
Обратите внимание на:
1. Какая модель дает наиболее релевантные результаты для ваших запросов
2. Насколько стабильны результаты между моделями (высокое пересечение = хорошо)
3. Различия в scores - более высокие scores обычно означают большую уверенность
4. Специфические случаи, где одна модель работает лучше других

Рекомендации:
- Если результаты сильно различаются, протестируйте на большем наборе запросов
- Если одна модель стабильно дает лучшие результаты, используйте её
- Учитывайте баланс между качеством и скоростью для вашего use case
    """)


if __name__ == "__main__":
    main()
