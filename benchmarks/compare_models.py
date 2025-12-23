"""
Сравнение различных моделей эмбеддингов для поиска по ТНВЭД.

Этот скрипт сравнивает производительность и качество поиска
для разных моделей эмбеддингов на русском языке.
"""

import sys
import os
import logging
import time
import random
import yaml
from typing import List, Dict, Tuple
import torch
from tabulate import tabulate

# Добавить корневую директорию проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.embedding_generator import EmbeddingGenerator
from services.text_normalizer import TextNormalizer
from services.tnved_searcher import TNVEDSearcher


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Модели для сравнения
MODELS_TO_COMPARE = [
    {
        "name": "FRIDA (текущая)",
        "model_id": "ai-forever/FRIDA",
        "size": "~3.1GB",
        "description": "Специализированная модель для русского языка"
    },
    {
        "name": "E5-Small",
        "model_id": "intfloat/multilingual-e5-small",
        "size": "~470MB",
        "description": "Компактная мультиязычная модель"
    },
    {
        "name": "MiniLM-L12",
        "model_id": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "size": "~470MB",
        "description": "Популярная мультиязычная модель"
    },
    {
        "name": "RuBERT-Tiny2",
        "model_id": "cointegrated/rubert-tiny2",
        "size": "~120MB",
        "description": "Очень компактная модель для русского"
    }
]


# Тестовые запросы для оценки качества поиска
TEST_QUERIES = [
    "кофе в зернах арабика",
    "свежие яблоки",
    "пшеничная мука высшего сорта",
    "натуральный мед",
    "оливковое масло extra virgin",
    "черный чай листовой",
    "молоко коровье пастеризованное",
    "сыр твердый",
    "шоколад темный",
    "минеральная вода газированная"
]


def load_config(config_path: str = None) -> dict:
    """Загрузить конфигурацию из YAML файла."""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def measure_embedding_speed(
    embedder: EmbeddingGenerator,
    texts: List[str],
    num_iterations: int = 3
) -> Tuple[float, float]:
    """
    Измерить скорость генерации эмбеддингов.
    
    Returns:
        Tuple[avg_time, embeddings_per_second]
    """
    times = []
    
    for _ in range(num_iterations):
        start = time.time()
        embedder.generate(texts, batch_size=32)
        elapsed = time.time() - start
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    embeddings_per_second = len(texts) / avg_time
    
    return avg_time, embeddings_per_second


def evaluate_search_quality(
    searcher: TNVEDSearcher,
    queries: List[str],
    top_k: int = 5
) -> Dict[str, float]:
    """
    Оценить качество поиска по тестовым запросам.
    
    Returns:
        Dict с метриками качества
    """
    total_time = 0
    results_count = []
    avg_scores = []
    
    for query in queries:
        start = time.time()
        results = searcher.search(query, top_k=top_k)
        elapsed = time.time() - start
        
        total_time += elapsed
        results_count.append(len(results))
        
        if results:
            avg_score = sum(r.similarity_score for r in results) / len(results)
            avg_scores.append(avg_score)
    
    return {
        "avg_search_time": total_time / len(queries),
        "avg_results_count": sum(results_count) / len(results_count),
        "avg_similarity_score": sum(avg_scores) / len(avg_scores) if avg_scores else 0.0
    }


def compare_models(config: dict, device: str = "cpu"):
    """Сравнить все модели."""
    logger.info("=" * 80)
    logger.info("СРАВНЕНИЕ МОДЕЛЕЙ ЭМБЕДДИНГОВ ДЛЯ ПОИСКА ПО ТНВЭД")
    logger.info("=" * 80)
    logger.info(f"Устройство: {device.upper()}")
    logger.info(f"CUDA доступна: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"CUDA память: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    logger.info("")
    logger.info("⚠️  ВНИМАНИЕ: Для корректного сравнения каждая модель использует свою коллекцию")
    logger.info("⚠️  Если коллекция не существует, она будет пропущена")
    logger.info("")
    
    # Инициализация общих компонентов
    normalizer = TextNormalizer()
    db_path = config["database"]["path"]
    base_collection_name = config["database"]["collection_name"]
    
    # Результаты сравнения
    comparison_results = []
    
    for model_info in MODELS_TO_COMPARE:
        logger.info("-" * 80)
        logger.info(f"Тестирование модели: {model_info['name']}")
        logger.info(f"ID: {model_info['model_id']}")
        logger.info(f"Размер: {model_info['size']}")
        logger.info(f"Описание: {model_info['description']}")
        logger.info("-" * 80)
        
        try:
            # Загрузка модели
            logger.info("Загрузка модели...")
            load_start = time.time()
            embedder = EmbeddingGenerator(
                model_name=model_info['model_id'],
                device=device
            )
            load_time = time.time() - load_start
            logger.info(f"✓ Модель загружена за {load_time:.2f}с")
            
            # Размерность эмбеддингов
            embedding_dim = embedder.get_embedding_dimension()
            logger.info(f"Размерность эмбеддингов: {embedding_dim}")
            
            # Измерение скорости генерации эмбеддингов
            logger.info("Измерение скорости генерации эмбеддингов...")
            avg_time, emb_per_sec = measure_embedding_speed(
                embedder,
                TEST_QUERIES,
                num_iterations=3
            )
            logger.info(f"✓ Скорость: {emb_per_sec:.2f} эмбеддингов/сек")
            
            # Оценка качества поиска
            logger.info("Оценка качества поиска...")
            
            # Используем коллекцию с именем модели для избежания конфликтов размерностей
            # Если коллекция не существует, пропускаем тест поиска
            model_collection_name = base_collection_name
            
            # Проверяем, совпадает ли размерность с существующей коллекцией
            try:
                # Пытаемся создать searcher
                searcher = TNVEDSearcher(
                    db_path=db_path,
                    normalizer=normalizer,
                    embedder=embedder,
                    collection_name=model_collection_name
                )
                
                # Пробуем выполнить тестовый поиск
                test_result = searcher.search(TEST_QUERIES[0], top_k=1)
                
                # Если успешно, выполняем полную оценку
                quality_metrics = evaluate_search_quality(searcher, TEST_QUERIES, top_k=5)
                logger.info(f"✓ Средняя скорость поиска: {quality_metrics['avg_search_time']:.3f}с")
                logger.info(f"✓ Средний score схожести: {quality_metrics['avg_similarity_score']:.4f}")
                
                # Пример поиска
                logger.info("\nПример поиска:")
                sample_query = random.choice(TEST_QUERIES)
                logger.info(f"Запрос: '{sample_query}'")
                results = searcher.search(sample_query, top_k=3)
                for i, result in enumerate(results, 1):
                    logger.info(
                        f"  {i}. {result.code} - {result.description[:60]}... "
                        f"(score: {result.similarity_score:.4f})"
                    )
                
            except Exception as search_error:
                logger.warning(f"⚠️  Поиск недоступен: {search_error}")
                logger.warning(f"⚠️  База данных создана с другой моделью (другая размерность эмбеддингов)")
                logger.warning(f"⚠️  Для тестирования поиска пересоздайте базу с этой моделью")
                
                # Устанавливаем значения по умолчанию
                quality_metrics = {
                    'avg_search_time': 0.0,
                    'avg_similarity_score': 0.0
                }
                
                logger.info("✓ Пропускаем тест поиска (несовместимая база данных)")
            
            # Сохранение результатов
            search_time_str = f"{quality_metrics['avg_search_time']:.3f}" if quality_metrics['avg_search_time'] > 0 else "N/A*"
            avg_score_str = f"{quality_metrics['avg_similarity_score']:.4f}" if quality_metrics['avg_similarity_score'] > 0 else "N/A*"
            
            comparison_results.append({
                "Модель": model_info['name'],
                "Размер": model_info['size'],
                "Размерность": embedding_dim,
                "Загрузка (с)": f"{load_time:.2f}",
                "Эмбеддинги/сек": f"{emb_per_sec:.2f}",
                "Поиск (с)": search_time_str,
                "Avg Score": avg_score_str
            })
            
            logger.info(f"✓ Модель {model_info['name']} протестирована успешно\n")
            
        except Exception as e:
            logger.error(f"✗ Ошибка при тестировании модели {model_info['name']}: {e}")
            comparison_results.append({
                "Модель": model_info['name'],
                "Размер": model_info['size'],
                "Размерность": "N/A",
                "Загрузка (с)": "ERROR",
                "Эмбеддинги/сек": "ERROR",
                "Поиск (с)": "ERROR",
                "Avg Score": "ERROR"
            })
    
    # Вывод итоговой таблицы
    logger.info("=" * 80)
    logger.info("ИТОГОВОЕ СРАВНЕНИЕ")
    logger.info("=" * 80)
    print("\n" + tabulate(comparison_results, headers="keys", tablefmt="grid"))
    print("\n* N/A - база данных несовместима (другая размерность эмбеддингов)")
    print("  Для тестирования поиска пересоздайте базу с нужной моделью")
    
    # Рекомендации
    logger.info("\n" + "=" * 80)
    logger.info("РЕКОМЕНДАЦИИ")
    logger.info("=" * 80)
    logger.info("• FRIDA - лучшее качество для русского языка, но медленная и большая")
    logger.info("• E5-Small - хороший баланс скорости и качества, поддержка CUDA")
    logger.info("• MiniLM-L12 - популярная и надежная, средняя скорость")
    logger.info("• RuBERT-Tiny2 - самая быстрая и компактная, для ограниченных ресурсов")
    logger.info("")
    logger.info("⚠️  ВАЖНО: Для полного тестирования поиска с выбранной моделью:")
    logger.info("   1. Обновите config.yaml с нужной моделью")
    logger.info("   2. Пересоздайте базу: python load_tnved.py")
    logger.info("   3. Запустите тест: python test_single_model.py <model_name>")


def main():
    """Главная функция."""
    # Загрузка конфигурации
    config = load_config()
    
    # Определение устройства
    device = config["model"].get("device", "cpu")
    if device == "cuda" and not torch.cuda.is_available():
        logger.warning("CUDA запрошена, но недоступна. Используется CPU.")
        device = "cpu"
    
    # Запуск сравнения
    compare_models(config, device=device)


if __name__ == "__main__":
    main()
