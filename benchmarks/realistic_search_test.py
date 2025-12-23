"""
Реалистичное тестирование поиска с запросами, соответствующими данным.

Этот скрипт тестирует поиск с запросами, похожими на описания товаров
на маркетплейсах, используя существующие базы данных.
"""

import sys
import os
import time
from typing import List, Dict
from tabulate import tabulate

# Добавить корневую директорию проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.embedding_generator import EmbeddingGenerator
from services.text_normalizer import TextNormalizer
from services.tnved_searcher import TNVEDSearcher


# Реалистичные тестовые запросы на основе данных в файле
TEST_QUERIES = {
    # Запросы, которые ДОЛЖНЫ найтись (товары есть в базе)
    "relevant": [
        "свежая говядина охлажденная для стейков",
        "филе трески замороженное для жарки",
        "куриные грудки охлажденные",
        "свиные ребрышки свежие",
        "мороженые креветки очищенные",
        "тушка индейки замороженная целая",
        "филе лосося свежее",
        "говяжья вырезка охлажденная премиум",
        "утиная грудка для запекания",
        "мясо краба мороженое",
        "свежая сельдь для засолки",
        "куриные окорочка охлажденные",
        "мороженая камбала целая",
        "свиная корейка без кости",
        "гусиная печень свежая",
    ],
    # Запросы, которых НЕТ в базе (для проверки поведения)
    "irrelevant": [
        "кофе в зернах арабика",
        "яблоки свежие красные",
        "молоко коровье пастеризованное",
        "хлеб пшеничный нарезной",
        "сыр твердый российский",
    ]
}


MODELS = [
    ("FRIDA", "ai-forever/FRIDA", "./benchmark_dbs/benchmark_frida"),
    ("E5-Small", "intfloat/multilingual-e5-small", "./benchmark_dbs/benchmark_e5_small"),
    ("MiniLM-L12", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "./benchmark_dbs/benchmark_miniLM_l12"),
    ("RuBERT-Tiny2", "cointegrated/rubert-tiny2", "./benchmark_dbs/benchmark_rubert_tiny2"),
]


def test_model_search(
    model_name: str,
    model_id: str,
    db_path: str,
    queries: List[str],
    top_k: int = 3
) -> Dict:
    """Тестировать поиск для одной модели."""
    
    print(f"\n{'='*80}")
    print(f"Модель: {model_name}")
    print(f"{'='*80}\n")
    
    if not os.path.exists(db_path):
        print(f"⚠️  База данных не найдена: {db_path}")
        return {"status": "error", "error": "Database not found"}
    
    # Инициализация
    normalizer = TextNormalizer()
    embedder = EmbeddingGenerator(model_name=model_id, device="cpu")
    searcher = TNVEDSearcher(
        db_path=db_path,
        normalizer=normalizer,
        embedder=embedder,
        collection_name="tnved"
    )
    
    results = []
    
    for query in queries:
        print(f"🔍 Запрос: '{query}'")
        
        try:
            start = time.time()
            search_results = searcher.search(query, top_k=top_k)
            search_time = time.time() - start
            
            if search_results:
                print(f"   ⏱️  Время: {search_time:.3f}с")
                print(f"   📊 Найдено: {len(search_results)} результатов")
                
                for i, result in enumerate(search_results, 1):
                    desc = result.description[:60] + "..." if len(result.description) > 60 else result.description
                    print(f"   {i}. [{result.similarity_score:.4f}] {result.code}")
                    print(f"      {desc}")
                
                results.append({
                    "query": query,
                    "time": search_time,
                    "count": len(search_results),
                    "top_score": search_results[0].similarity_score,
                    "avg_score": sum(r.similarity_score for r in search_results) / len(search_results),
                    "top_result": search_results[0].description[:80]
                })
            else:
                print(f"   ⚠️  Результатов не найдено")
                results.append({
                    "query": query,
                    "time": search_time,
                    "count": 0,
                    "top_score": 0.0,
                    "avg_score": 0.0,
                    "top_result": "N/A"
                })
            
            print()
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}\n")
            results.append({
                "query": query,
                "error": str(e)
            })
    
    return {
        "status": "success",
        "model_name": model_name,
        "results": results
    }


def generate_comparison_report(all_results: List[Dict]):
    """Генерировать сравнительный отчет."""
    
    print("\n" + "="*80)
    print("СРАВНИТЕЛЬНЫЙ АНАЛИЗ")
    print("="*80 + "\n")
    
    # Таблица средних метрик
    summary_data = []
    
    for model_result in all_results:
        if model_result["status"] == "success":
            results = model_result["results"]
            valid_results = [r for r in results if "error" not in r and r["count"] > 0]
            
            if valid_results:
                avg_time = sum(r["time"] for r in valid_results) / len(valid_results)
                avg_top_score = sum(r["top_score"] for r in valid_results) / len(valid_results)
                avg_avg_score = sum(r["avg_score"] for r in valid_results) / len(valid_results)
                
                summary_data.append([
                    model_result["model_name"],
                    f"{avg_time:.3f}",
                    f"{avg_top_score:.4f}",
                    f"{avg_avg_score:.4f}",
                    len(valid_results)
                ])
    
    print("Средние показатели по всем запросам:\n")
    print(tabulate(
        summary_data,
        headers=["Модель", "Время (с)", "Top Score", "Avg Score", "Успешных"],
        tablefmt="grid"
    ))
    
    # Анализ по типам запросов
    print("\n" + "="*80)
    print("АНАЛИЗ ПО ТИПАМ ЗАПРОСОВ")
    print("="*80 + "\n")
    
    for query_type, queries in TEST_QUERIES.items():
        print(f"\n{'─'*80}")
        if query_type == "relevant":
            print("РЕЛЕВАНТНЫЕ ЗАПРОСЫ (товары есть в базе)")
        else:
            print("НЕРЕЛЕВАНТНЫЕ ЗАПРОСЫ (товаров нет в базе)")
        print(f"{'─'*80}\n")
        
        type_summary = []
        
        for model_result in all_results:
            if model_result["status"] == "success":
                model_name = model_result["model_name"]
                results = model_result["results"]
                
                # Фильтровать результаты по типу запроса
                type_results = [r for r in results if r["query"] in queries and "error" not in r and r["count"] > 0]
                
                if type_results:
                    avg_top_score = sum(r["top_score"] for r in type_results) / len(type_results)
                    avg_avg_score = sum(r["avg_score"] for r in type_results) / len(type_results)
                    
                    type_summary.append([
                        model_name,
                        f"{avg_top_score:.4f}",
                        f"{avg_avg_score:.4f}",
                        len(type_results)
                    ])
        
        if type_summary:
            print(tabulate(
                type_summary,
                headers=["Модель", "Top Score", "Avg Score", "Запросов"],
                tablefmt="grid"
            ))
    
    # Рекомендации
    print("\n" + "="*80)
    print("ВЫВОДЫ И РЕКОМЕНДАЦИИ")
    print("="*80 + "\n")
    
    if summary_data:
        # Лучшая по качеству
        best_quality = max(summary_data, key=lambda x: float(x[2]))
        print(f"🎯 Лучшее качество: {best_quality[0]}")
        print(f"   Top Score: {best_quality[2]}")
        
        # Самая быстрая
        fastest = min(summary_data, key=lambda x: float(x[1]))
        print(f"\n⚡ Самая быстрая: {fastest[0]}")
        print(f"   Время: {fastest[1]}с")
        
        # Лучший баланс
        for row in summary_data:
            # Нормализованная оценка (качество важнее скорости)
            quality_score = float(row[2])
            speed_score = 1.0 / (float(row[1]) + 0.001)  # Инвертировать время
            balance = quality_score * 0.7 + (speed_score / 100) * 0.3  # 70% качество, 30% скорость
            row.append(balance)
        
        best_balance = max(summary_data, key=lambda x: x[-1])
        print(f"\n⚖️  Лучший баланс: {best_balance[0]}")
        print(f"   Комплексная оценка: {best_balance[-1]:.4f}")


def main():
    """Главная функция."""
    
    print("="*80)
    print("РЕАЛИСТИЧНОЕ ТЕСТИРОВАНИЕ ПОИСКА")
    print("="*80)
    print(f"\nРелевантных запросов: {len(TEST_QUERIES['relevant'])}")
    print(f"Нерелевантных запросов: {len(TEST_QUERIES['irrelevant'])}")
    print(f"Всего запросов: {len(TEST_QUERIES['relevant']) + len(TEST_QUERIES['irrelevant'])}")
    print(f"Моделей для тестирования: {len(MODELS)}\n")
    
    all_results = []
    
    # Тестирование каждой модели
    for model_name, model_id, db_path in MODELS:
        # Объединить все запросы
        all_queries = TEST_QUERIES["relevant"] + TEST_QUERIES["irrelevant"]
        
        result = test_model_search(
            model_name=model_name,
            model_id=model_id,
            db_path=db_path,
            queries=all_queries,
            top_k=3
        )
        
        all_results.append(result)
    
    # Генерация отчета
    generate_comparison_report(all_results)
    
    print("\n" + "="*80)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*80)


if __name__ == "__main__":
    main()
