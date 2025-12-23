"""
Полное автоматизированное сравнение моделей эмбеддингов.

Этот скрипт автоматически:
1. Создает отдельную базу данных для каждой модели
2. Загружает данные из Excel
3. Тестирует скорость и качество поиска
4. Генерирует итоговый отчет

Использование:
    python benchmarks/full_model_benchmark.py tnved_1-1000.xlsx
"""

import sys
import os
import time
import yaml
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import torch
from tabulate import tabulate

# Добавить корневую директорию проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.embedding_generator import EmbeddingGenerator
from services.text_normalizer import TextNormalizer
from services.tnved_loader import TNVEDLoader
from services.tnved_searcher import TNVEDSearcher


# Модели для тестирования
MODELS = [
    {
        "name": "FRIDA",
        "model_id": "ai-forever/FRIDA",
        "size": "~3.1GB",
        "description": "Специализированная для русского"
    },
    {
        "name": "E5-Small",
        "model_id": "intfloat/multilingual-e5-small",
        "size": "~470MB",
        "description": "Компактная мультиязычная"
    },
    {
        "name": "MiniLM-L12",
        "model_id": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "size": "~470MB",
        "description": "Популярная мультиязычная"
    },
    {
        "name": "RuBERT-Tiny2",
        "model_id": "cointegrated/rubert-tiny2",
        "size": "~120MB",
        "description": "Очень компактная для русского"
    }
]


# Тестовые запросы
TEST_QUERIES = [
    "кофе в зернах арабика",
    "свежие яблоки",
    "пшеничная мука высшего сорта",
    "натуральный мед",
    "оливковое масло",
    "черный чай листовой",
    "молоко коровье",
    "сыр твердый",
    "шоколад темный",
    "минеральная вода"
]


def print_header(text: str):
    """Печать заголовка."""
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80 + "\n")


def print_section(text: str):
    """Печать секции."""
    print("\n" + "-" * 80)
    print(text)
    print("-" * 80)


def load_and_index_data(
    excel_file: str,
    model_name: str,
    model_id: str,
    db_path: str,
    device: str = "cpu",
    batch_size: int = 50
) -> Tuple[float, int]:
    """
    Загрузить и проиндексировать данные для модели.
    
    Returns:
        Tuple[load_time, records_count]
    """
    print(f"📊 Загрузка данных для модели: {model_name}")
    print(f"   Модель: {model_id}")
    print(f"   База данных: {db_path}")
    print(f"   Устройство: {device}")
    
    # Создать директорию для базы данных
    os.makedirs(db_path, exist_ok=True)
    
    # Инициализация компонентов
    normalizer = TextNormalizer()
    embedder = EmbeddingGenerator(model_name=model_id, device=device)
    
    loader = TNVEDLoader(
        db_path=db_path,
        normalizer=normalizer,
        embedder=embedder,
        batch_size=batch_size,
        collection_name="tnved"
    )
    
    # Загрузка данных
    start_time = time.time()
    records_loaded = loader.load_from_excel(excel_file)
    load_time = time.time() - start_time
    
    print(f"   ✓ Загружено {records_loaded} записей за {load_time:.2f}с")
    print(f"   ✓ Скорость: {records_loaded/load_time:.2f} записей/сек\n")
    
    return load_time, records_loaded


def test_search_quality(
    model_name: str,
    model_id: str,
    db_path: str,
    device: str = "cpu"
) -> Dict:
    """
    Тестировать качество поиска для модели.
    
    Returns:
        Dict с метриками
    """
    print(f"🔍 Тестирование поиска для модели: {model_name}")
    
    # Инициализация компонентов
    normalizer = TextNormalizer()
    embedder = EmbeddingGenerator(model_name=model_id, device=device)
    
    searcher = TNVEDSearcher(
        db_path=db_path,
        normalizer=normalizer,
        embedder=embedder,
        collection_name="tnved"
    )
    
    # Тестирование поиска
    search_times = []
    avg_scores = []
    all_results = []
    
    for query in TEST_QUERIES:
        start = time.time()
        results = searcher.search(query, top_k=5)
        search_time = time.time() - start
        
        search_times.append(search_time)
        
        if results:
            avg_score = sum(r.similarity_score for r in results) / len(results)
            avg_scores.append(avg_score)
            all_results.append((query, results))
    
    metrics = {
        "avg_search_time": sum(search_times) / len(search_times),
        "min_search_time": min(search_times),
        "max_search_time": max(search_times),
        "avg_similarity_score": sum(avg_scores) / len(avg_scores) if avg_scores else 0.0,
        "min_similarity_score": min(avg_scores) if avg_scores else 0.0,
        "max_similarity_score": max(avg_scores) if avg_scores else 0.0,
        "sample_results": all_results[:3]  # Первые 3 примера
    }
    
    print(f"   ✓ Средняя скорость поиска: {metrics['avg_search_time']:.3f}с")
    print(f"   ✓ Средний similarity score: {metrics['avg_similarity_score']:.4f}")
    print(f"   ✓ Диапазон scores: {metrics['min_similarity_score']:.4f} - {metrics['max_similarity_score']:.4f}\n")
    
    return metrics


def benchmark_model(
    model_info: Dict,
    excel_file: str,
    base_db_path: str,
    device: str = "cpu"
) -> Dict:
    """
    Полное тестирование одной модели.
    
    Returns:
        Dict с результатами
    """
    model_name = model_info["name"]
    model_id = model_info["model_id"]
    
    print_section(f"Тестирование модели: {model_name}")
    
    # Создать уникальную директорию для базы данных этой модели
    db_path = os.path.join(base_db_path, f"benchmark_{model_name.lower().replace('-', '_')}")
    
    # Удалить старую базу если существует
    if os.path.exists(db_path):
        print(f"⚠️  Удаление старой базы данных: {db_path}")
        shutil.rmtree(db_path)
    
    results = {
        "name": model_name,
        "model_id": model_id,
        "size": model_info["size"],
        "description": model_info["description"]
    }
    
    try:
        # 1. Загрузка модели и измерение времени
        print("📦 Загрузка модели...")
        load_start = time.time()
        embedder = EmbeddingGenerator(model_name=model_id, device=device)
        model_load_time = time.time() - load_start
        embedding_dim = embedder.get_embedding_dimension()
        
        print(f"   ✓ Модель загружена за {model_load_time:.2f}с")
        print(f"   ✓ Размерность эмбеддингов: {embedding_dim}\n")
        
        results["model_load_time"] = model_load_time
        results["embedding_dim"] = embedding_dim
        
        # 2. Загрузка и индексация данных
        data_load_time, records_count = load_and_index_data(
            excel_file=excel_file,
            model_name=model_name,
            model_id=model_id,
            db_path=db_path,
            device=device,
            batch_size=50
        )
        
        results["data_load_time"] = data_load_time
        results["records_count"] = records_count
        results["indexing_speed"] = records_count / data_load_time
        
        # 3. Тестирование поиска
        search_metrics = test_search_quality(
            model_name=model_name,
            model_id=model_id,
            db_path=db_path,
            device=device
        )
        
        results.update(search_metrics)
        results["status"] = "success"
        
        print(f"✅ Модель {model_name} протестирована успешно!\n")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании модели {model_name}: {e}\n")
        results["status"] = "error"
        results["error"] = str(e)
    
    return results


def generate_report(all_results: List[Dict], output_file: str):
    """Генерировать итоговый отчет."""
    
    print_header("ИТОГОВЫЙ ОТЧЕТ")
    
    # Таблица сравнения
    table_data = []
    for result in all_results:
        if result["status"] == "success":
            row = [
                result["name"],
                result["size"],
                result["embedding_dim"],
                f"{result['model_load_time']:.2f}",
                f"{result['indexing_speed']:.2f}",
                f"{result['avg_search_time']:.3f}",
                f"{result['avg_similarity_score']:.4f}"
            ]
        else:
            row = [
                result["name"],
                result["size"],
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR",
                "ERROR"
            ]
        table_data.append(row)
    
    headers = [
        "Модель",
        "Размер",
        "Размерность",
        "Загрузка (с)",
        "Индексация (зап/с)",
        "Поиск (с)",
        "Avg Score"
    ]
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Примеры результатов поиска
    print("\n" + "=" * 80)
    print("ПРИМЕРЫ РЕЗУЛЬТАТОВ ПОИСКА")
    print("=" * 80)
    
    for result in all_results:
        if result["status"] == "success" and "sample_results" in result:
            print(f"\n{'─' * 80}")
            print(f"Модель: {result['name']}")
            print(f"{'─' * 80}")
            
            for query, results in result["sample_results"][:2]:  # Первые 2 запроса
                print(f"\nЗапрос: '{query}'")
                for i, r in enumerate(results[:3], 1):  # Топ-3 результата
                    desc = r.description[:50] + "..." if len(r.description) > 50 else r.description
                    print(f"  {i}. {r.code} - {desc} (score: {r.similarity_score:.4f})")
    
    # Рекомендации
    print("\n" + "=" * 80)
    print("РЕКОМЕНДАЦИИ")
    print("=" * 80)
    
    successful_results = [r for r in all_results if r["status"] == "success"]
    
    if successful_results:
        # Самая быстрая индексация
        fastest_indexing = max(successful_results, key=lambda x: x["indexing_speed"])
        print(f"\n🚀 Самая быстрая индексация: {fastest_indexing['name']}")
        print(f"   {fastest_indexing['indexing_speed']:.2f} записей/сек")
        
        # Самый быстрый поиск
        fastest_search = min(successful_results, key=lambda x: x["avg_search_time"])
        print(f"\n⚡ Самый быстрый поиск: {fastest_search['name']}")
        print(f"   {fastest_search['avg_search_time']:.3f}с в среднем")
        
        # Лучшее качество
        best_quality = max(successful_results, key=lambda x: x["avg_similarity_score"])
        print(f"\n🎯 Лучшее качество: {best_quality['name']}")
        print(f"   {best_quality['avg_similarity_score']:.4f} средний score")
        
        # Лучший баланс (нормализованная оценка)
        for r in successful_results:
            # Нормализация метрик (0-1, где 1 - лучше)
            max_indexing = max(x["indexing_speed"] for x in successful_results)
            min_search = min(x["avg_search_time"] for x in successful_results)
            max_search = max(x["avg_search_time"] for x in successful_results)
            max_score = max(x["avg_similarity_score"] for x in successful_results)
            
            norm_indexing = r["indexing_speed"] / max_indexing
            norm_search = 1 - ((r["avg_search_time"] - min_search) / (max_search - min_search)) if max_search > min_search else 1
            norm_quality = r["avg_similarity_score"] / max_score if max_score > 0 else 0
            
            r["balance_score"] = (norm_indexing + norm_search + norm_quality) / 3
        
        best_balance = max(successful_results, key=lambda x: x["balance_score"])
        print(f"\n⚖️  Лучший баланс: {best_balance['name']}")
        print(f"   Комплексная оценка: {best_balance['balance_score']:.3f}")
    
    # Сохранение отчета в файл
    print(f"\n📄 Сохранение отчета в: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Отчет о сравнении моделей эмбеддингов\n\n")
        f.write(f"Дата: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Устройство: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}\n\n")
        
        f.write("## Сравнительная таблица\n\n")
        f.write(tabulate(table_data, headers=headers, tablefmt="github"))
        f.write("\n\n")
        
        f.write("## Детальные результаты\n\n")
        for result in all_results:
            f.write(f"### {result['name']}\n\n")
            if result["status"] == "success":
                f.write(f"- **Размер**: {result['size']}\n")
                f.write(f"- **Размерность**: {result['embedding_dim']}\n")
                f.write(f"- **Загрузка модели**: {result['model_load_time']:.2f}с\n")
                f.write(f"- **Скорость индексации**: {result['indexing_speed']:.2f} записей/сек\n")
                f.write(f"- **Средняя скорость поиска**: {result['avg_search_time']:.3f}с\n")
                f.write(f"- **Средний similarity score**: {result['avg_similarity_score']:.4f}\n")
                f.write(f"- **Диапазон scores**: {result['min_similarity_score']:.4f} - {result['max_similarity_score']:.4f}\n")
            else:
                f.write(f"- **Статус**: Ошибка\n")
                f.write(f"- **Ошибка**: {result.get('error', 'Unknown')}\n")
            f.write("\n")
    
    print(f"✅ Отчет сохранен!\n")


def main():
    """Главная функция."""
    if len(sys.argv) < 2:
        print("Использование: python benchmarks/full_model_benchmark.py <excel_file>")
        print("Пример: python benchmarks/full_model_benchmark.py tnved_1-1000.xlsx")
        sys.exit(1)
    
    excel_file = sys.argv[1]
    
    if not os.path.exists(excel_file):
        print(f"❌ Файл не найден: {excel_file}")
        sys.exit(1)
    
    print_header("ПОЛНОЕ СРАВНЕНИЕ МОДЕЛЕЙ ЭМБЕДДИНГОВ")
    
    print(f"📁 Файл данных: {excel_file}")
    print(f"🖥️  Устройство: {'GPU - ' + torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    print(f"📊 Моделей для тестирования: {len(MODELS)}")
    print(f"🔍 Тестовых запросов: {len(TEST_QUERIES)}")
    
    # Определить устройство
    device = "cpu"  # Используем CPU для стабильности
    
    # Базовая директория для баз данных
    base_db_path = "./benchmark_dbs"
    os.makedirs(base_db_path, exist_ok=True)
    
    # Тестирование всех моделей
    all_results = []
    
    for i, model_info in enumerate(MODELS, 1):
        print(f"\n{'█' * 80}")
        print(f"Модель {i}/{len(MODELS)}: {model_info['name']}")
        print(f"{'█' * 80}")
        
        result = benchmark_model(
            model_info=model_info,
            excel_file=excel_file,
            base_db_path=base_db_path,
            device=device
        )
        
        all_results.append(result)
    
    # Генерация отчета
    output_file = "docs/BENCHMARK_REPORT.md"
    generate_report(all_results, output_file)
    
    print_header("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
    print(f"📄 Полный отчет: {output_file}")
    print(f"📁 Базы данных: {base_db_path}/")


if __name__ == "__main__":
    main()
