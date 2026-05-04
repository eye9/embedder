#!/usr/bin/env python3
"""
CLI скрипт для пакетной обработки Excel файлов с подбором ТНВЭД кодов.

Использует тот же алгоритм, что и веб-интерфейс, включая:
- Подбор через URL (если есть колонка URL)
- Семантический поиск
- Гибридный режим с приоритетом URL

Использование:
    python batch_process_cli.py input.xlsx output.xlsx --config config.yaml
"""

import sys
import argparse
import logging
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any
import time

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from batch_processor.services.enhanced_excel_processor import EnhancedExcelProcessor
from batch_processor.services.tnved_integration import get_tnved_integration
from batch_processor.config.settings import get_config
from services.hybrid_selector import HybridSelector, URLPriority
from services.url_matcher import URLMatcher
from services.url_database_manager import URLDatabaseManager
from services.chroma_manager import ChromaDBManager
from utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


def process_excel_file(
    input_file: Path,
    output_file: Path,
    process_mode: str = "all",
    algorithm: str = "similarity_top1",
    use_url_processing: bool = True,
    url_priority: str = "first",
    confidence_threshold: float = 0.185
) -> None:
    """
    Обработка Excel файла с подбором ТНВЭД кодов.
    
    Использует тот же алгоритм, что и веб-интерфейс:
    - Hybrid selector с поддержкой URL
    - Семантический поиск как fallback
    - Раскрашивание ячеек по confidence score
    
    Args:
        input_file: Путь к входному Excel файлу
        output_file: Путь к выходному Excel файлу
        process_mode: Режим обработки ("all" или "empty_only")
        algorithm: Алгоритм подбора ("similarity_top1" или "llm_reasoning")
        use_url_processing: Использовать подбор через URL
        url_priority: Приоритет URL ("first", "only", "disabled")
        confidence_threshold: Порог уверенности для раскрашивания
    """
    start_time = time.time()
    
    logger.info("=" * 70)
    logger.info("BATCH EXCEL PROCESSOR - CLI MODE")
    logger.info("=" * 70)
    logger.info(f"Input file:       {input_file}")
    logger.info(f"Output file:      {output_file}")
    logger.info(f"Mode:             {process_mode}")
    logger.info(f"Algorithm:        {algorithm}")
    logger.info(f"URL processing:   {use_url_processing}")
    logger.info(f"URL priority:     {url_priority}")
    logger.info("=" * 70)
    
    # Загрузка конфигурации
    try:
        config = get_config()
        logger.info("✓ Configuration loaded")
        logger.info(f"  Model: {config.model.name if hasattr(config, 'model') else 'default'}")
        logger.info(f"  Device: {config.model.device if hasattr(config, 'model') else 'cpu'}")
        logger.info(f"  Chunk size: {config.processing.chunk_size}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise
    
    # Инициализация компонентов
    logger.info("Initializing components...")
    
    try:
        # Excel processor
        excel_processor = EnhancedExcelProcessor(chunk_size=config.processing.chunk_size)
        
        # TNVED integration
        tnved_integration = get_tnved_integration()
        
        logger.info("✓ Components initialized")
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        raise
    
    # Валидация файла
    logger.info("Validating file...")
    is_valid, error_msg, total_rows, has_url_column = excel_processor.validate_file_with_url_support(input_file)
    
    if not is_valid:
        raise ValueError(f"File validation failed: {error_msg}")
    
    logger.info(f"✓ File validated: {total_rows} rows, has_url_column: {has_url_column}")
    
    # Определение стратегии обработки
    processing_strategy = excel_processor.determine_processing_strategy(input_file)
    logger.info(f"Processing strategy: {processing_strategy['strategy']} - {processing_strategy['reason']}")
    
    # Создание селектора
    logger.info("Creating selector...")
    
    try:
        if processing_strategy['recommended_selector'] == 'hybrid' and has_url_column and use_url_processing:
            # Создать hybrid selector с поддержкой URL
            selector = _create_hybrid_selector(
                tnved_integration=tnved_integration,
                algorithm=algorithm,
                url_priority=url_priority
            )
            use_hybrid_processing = True
            logger.info(f"✓ Using hybrid selector with URL priority: {url_priority}")
        else:
            # Создать стандартный semantic selector
            selector = tnved_integration.create_selector(algorithm)
            use_hybrid_processing = False
            logger.info(f"✓ Using standard {algorithm} selector")
    except Exception as e:
        logger.error(f"Failed to create selector: {e}")
        raise
    
    # Получение информации о файле
    file_info = excel_processor.get_file_info(input_file)
    
    if process_mode == "empty_only":
        rows_to_process = file_info['rows_with_descriptions'] - file_info['rows_with_existing_codes']
    else:
        rows_to_process = file_info['rows_with_descriptions']
    
    logger.info(f"Processing {rows_to_process} rows in {process_mode} mode")
    
    # Обработка файла
    logger.info("")
    logger.info("Processing rows...")
    logger.info("-" * 70)
    
    results = []
    processed_count = 0
    error_count = 0
    url_match_count = 0
    semantic_match_count = 0
    row_colors = {}  # Для раскрашивания
    
    if use_hybrid_processing:
        # Обработка с hybrid selector (как в веб-интерфейсе)
        for hybrid_result in excel_processor.process_file_with_hybrid_selector(
            input_file, selector, process_mode
        ):
            # Конвертировать в стандартный результат
            result = hybrid_result.to_processing_result()
            results.append(result)
            processed_count += 1
            
            # Отслеживание источников совпадений
            if hybrid_result.match_source == "url":
                url_match_count += 1
            elif hybrid_result.match_source == "semantic":
                semantic_match_count += 1
            
            if not result.is_successful():
                error_count += 1
            
            # Сохранить confidence score для раскрашивания
            if result.confidence_score is not None:
                row_colors[result.row_index] = result.confidence_score
            
            # Прогресс
            if processed_count % 100 == 0:
                progress = (processed_count / rows_to_process * 100) if rows_to_process > 0 else 100
                logger.info(
                    f"Progress: {processed_count}/{rows_to_process} ({progress:.1f}%) "
                    f"[URL: {url_match_count}, Semantic: {semantic_match_count}, Errors: {error_count}]"
                )
    else:
        # Обработка со стандартным selector
        for result in excel_processor.process_file_with_backward_compatibility(
            input_file, selector, process_mode
        ):
            results.append(result)
            processed_count += 1
            semantic_match_count += 1
            
            if not result.is_successful():
                error_count += 1
            
            # Сохранить confidence score для раскрашивания
            if result.confidence_score is not None:
                row_colors[result.row_index] = result.confidence_score
            
            # Прогресс
            if processed_count % 100 == 0:
                progress = (processed_count / rows_to_process * 100) if rows_to_process > 0 else 100
                logger.info(
                    f"Progress: {processed_count}/{rows_to_process} ({progress:.1f}%) "
                    f"[Errors: {error_count}]"
                )
    
    # Генерация выходного файла
    logger.info("")
    logger.info("Generating output file...")
    
    try:
        # Конвертировать результаты в словарь для Excel processor
        results_dict = []
        for result in results:
            results_dict.append({
                'row_index': result.row_index,
                'tnved_code': result.tnved_code or '',
                'selection_reason': result.selection_reason,
                'confidence_score': result.confidence_score
            })
        
        # Записать результаты
        preserve_existing = (process_mode == "empty_only")
        excel_processor.write_results(
            input_file,
            results_dict,
            output_file,
            preserve_existing_hts=preserve_existing
        )
        
        logger.info(f"✓ Results saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Failed to generate output file: {e}")
        raise
    
    # Статистика
    elapsed_time = time.time() - start_time
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("PROCESSING COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Successfully processed: {processed_count}")
    logger.info(f"Errors:                {error_count}")
    if use_hybrid_processing:
        logger.info(f"URL matches:           {url_match_count}")
        logger.info(f"Semantic matches:      {semantic_match_count}")
        url_match_rate = (url_match_count / processed_count * 100) if processed_count > 0 else 0
        logger.info(f"URL match rate:        {url_match_rate:.1f}%")
    logger.info(f"Total time:            {elapsed_time:.2f} seconds")
    logger.info(f"Processing rate:       {processed_count / elapsed_time:.2f} records/second")
    logger.info(f"Output file:           {output_file}")
    logger.info("=" * 70)


def _create_hybrid_selector(
    tnved_integration,
    algorithm: str,
    url_priority: str,
    **kwargs
) -> HybridSelector:
    """
    Создать hybrid selector с поддержкой URL (как в веб-интерфейсе).
    
    Args:
        tnved_integration: TNVEDSystemIntegration instance
        algorithm: Базовый семантический алгоритм
        url_priority: Приоритет URL ("first", "only", "disabled")
        **kwargs: Дополнительные параметры
        
    Returns:
        HybridSelector instance
    """
    try:
        # Создать semantic selector
        semantic_selector = tnved_integration.create_selector(algorithm, **kwargs)
        
        # Инициализировать URL компоненты
        chroma_manager = ChromaDBManager(db_path="./chroma_db")
        url_db_manager = URLDatabaseManager(
            chroma_client=chroma_manager.client,
            collection_name="url_tnved_mapping"
        )
        url_matcher = URLMatcher(url_db_manager)
        
        # Парсинг URL priority
        try:
            priority_enum = URLPriority(url_priority.lower())
        except ValueError:
            logger.warning(f"Invalid URL priority '{url_priority}', defaulting to 'first'")
            priority_enum = URLPriority.FIRST
        
        # Создать hybrid selector
        hybrid_selector = HybridSelector(
            url_matcher=url_matcher,
            semantic_selector=semantic_selector,
            url_priority=priority_enum,
            url_timeout_seconds=kwargs.get('url_timeout_seconds', 5.0),
            verbose_reasons=kwargs.get('verbose_reasons', True)
        )
        
        logger.info(f"Created hybrid selector with {algorithm} semantic backend and {url_priority} URL priority")
        return hybrid_selector
        
    except Exception as e:
        logger.error(f"Failed to create hybrid selector: {e}")
        raise


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Batch Excel Processor - CLI Mode (same algorithm as web interface)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (with URL processing)
  python batch_process_cli.py input.xlsx output.xlsx

  # With config file
  python batch_process_cli.py input.xlsx output.xlsx --config config.yaml

  # Process only empty rows
  python batch_process_cli.py input.xlsx output.xlsx --mode empty_only

  # Disable URL processing (semantic only)
  python batch_process_cli.py input.xlsx output.xlsx --url-processing disabled

  # URL-only mode (no semantic fallback)
  python batch_process_cli.py input.xlsx output.xlsx --url-priority only

  # With verbose logging
  python batch_process_cli.py input.xlsx output.xlsx --log-level DEBUG
        """
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to input Excel file"
    )
    parser.add_argument(
        "output_file",
        type=Path,
        help="Path to output Excel file"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (optional, uses batch_processor_config.yaml by default)"
    )
    parser.add_argument(
        "--mode",
        choices=["all", "empty_only"],
        default="all",
        help="Processing mode: all (all rows) or empty_only (only empty rows)"
    )
    parser.add_argument(
        "--algorithm",
        choices=["similarity_top1", "llm_reasoning"],
        default="similarity_top1",
        help="Selection algorithm (default: similarity_top1)"
    )
    parser.add_argument(
        "--url-processing",
        choices=["enabled", "disabled"],
        default="enabled",
        help="Enable/disable URL processing (default: enabled)"
    )
    parser.add_argument(
        "--url-priority",
        choices=["first", "only", "disabled"],
        default="first",
        help="URL priority mode: first (try URL first), only (URL only), disabled (semantic only)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.185,
        help="Confidence threshold for color coding (default: 0.185)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Настройка логирования
    setup_logging(level=args.log_level)
    
    # Загрузка конфигурации (если указан --config, он будет использован)
    # Иначе система использует batch_processor_config.yaml или переменные окружения
    if args.config:
        if not args.config.exists():
            logger.error(f"Config file not found: {args.config}")
            sys.exit(1)
        logger.info(f"Using config file: {args.config}")
        # Установить переменную окружения для конфига
        import os
        os.environ['BATCH_PROCESSOR_CONFIG'] = str(args.config.absolute())
    
    # Проверка входного файла
    if not args.input_file.exists():
        logger.error(f"Input file not found: {args.input_file}")
        sys.exit(1)
    
    # Определить параметры URL processing
    use_url_processing = (args.url_processing == "enabled")
    url_priority = args.url_priority if use_url_processing else "disabled"
    
    # Обработка файла
    try:
        process_excel_file(
            input_file=args.input_file,
            output_file=args.output_file,
            process_mode=args.mode,
            algorithm=args.algorithm,
            use_url_processing=use_url_processing,
            url_priority=url_priority,
            confidence_threshold=args.threshold
        )
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
