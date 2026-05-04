"""
Скрипт для загрузки данных из import_26-01.xlsx в базу данных URL.
Дедупликация: не загружаются записи с одинаковыми описаниями и кодами.
Использует настройки из config.yaml для GPU и batch_size.
"""

import pandas as pd
import chromadb
import sys
from chromadb.config import Settings
import logging
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from services.url_database_manager_optimized import OptimizedURLDatabaseManager
from utils.config import Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def load_import_data(excel_file: str = str(PROJECT_ROOT / "xlsx" / "import_26-01.xlsx")):
    """
    Загружает данные из Excel файла в базу данных URL.
    Дедупликация по описанию и коду.
    
    Args:
        excel_file: Путь к Excel файлу
    """
    start_time = time.time()
    
    # Загрузка конфигурации
    config_path = PROJECT_ROOT / "config.yaml"
    logger.info(f"Загрузка конфигурации из {config_path}")
    config = Config.from_file(str(config_path))
    
    # Получение настроек
    db_path = config.database.path
    batch_size = config.processing.batch_size
    device = config.model.device
    
    logger.info(f"Настройки: device={device}, batch_size={batch_size}, db_path={db_path}")
    
    # Инициализация ChromaDB
    logger.info(f"Начало загрузки данных из {excel_file}")
    chroma_client = chromadb.PersistentClient(
        path=db_path,
        settings=Settings(anonymized_telemetry=False)
    )
    db_manager = OptimizedURLDatabaseManager(chroma_client, "url_tnved_mapping")
    
    # Чтение файла
    logger.info("Чтение Excel файла...")
    df = pd.read_excel(excel_file)
    logger.info(f"Прочитано {len(df)} записей")
    logger.info(f"Колонки: {df.columns.tolist()}")
    
    # Проверка наличия необходимых колонок
    required_columns = ['Code', 'Description', 'URL']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Отсутствуют необходимые колонки: {missing_columns}")
    
    # Удаление записей с пустыми значениями (Description опционально)
    initial_count = len(df)
    df = df.dropna(subset=['Code', 'URL'])
    df['Description'] = df['Description'].fillna('')
    logger.info(f"После удаления пустых значений: {len(df)} записей (удалено {initial_count - len(df)})")
    
    # Дедупликация только по URL (каждый URL уникален)
    logger.info("Дедупликация по URL...")
    before_dedup = len(df)
    df = df.drop_duplicates(subset=['URL'], keep='first')
    logger.info(f"После дедупликации по URL: {len(df)} записей (удалено дубликатов: {before_dedup - len(df)})")
    
    # Нормализация кодов (добавление нулей до 10 символов)
    df['Code'] = df['Code'].astype(str).str.strip().str.zfill(10)
    df['Description'] = df['Description'].astype(str).str.strip()
    
    # Загрузка в базу данных используя оптимизированный метод
    logger.info(f"Загрузка данных в базу (batch_size={batch_size})...")
    stats = db_manager.batch_load_from_dataframe(
        df=df,
        source_name="import_26-01",
        url_column="URL",
        code_column="Code",
        description_column="Description",
        batch_size=batch_size
    )
    
    # Статистика
    elapsed_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info("РЕЗУЛЬТАТЫ ЗАГРУЗКИ")
    logger.info("=" * 60)
    logger.info(f"Всего записей в файле: {initial_count}")
    logger.info(f"После очистки и дедупликации по URL: {len(df)}")
    logger.info(f"Успешно загружено: {stats['success']}")
    logger.info(f"Невалидных URL: {stats['invalid_urls']}")
    logger.info(f"Невалидных кодов: {stats['invalid_codes']}")
    logger.info(f"Время выполнения: {elapsed_time:.2f} сек ({elapsed_time/60:.2f} мин)")
    logger.info(f"Скорость: {stats['success']/elapsed_time:.1f} записей/сек")
    logger.info("=" * 60)
    
    # Проверка итогового размера базы
    db_stats = db_manager.get_statistics()
    logger.info(f"Всего записей в базе данных: {db_stats['total_records']}")
    
    return stats['success'], stats['invalid_urls'], stats['invalid_codes']


if __name__ == "__main__":
    try:
        success, invalid_urls, invalid_codes = load_import_data()
        print(f"\n✓ Загрузка завершена:")
        print(f"  - Успешно загружено: {success}")
        print(f"  - Невалидных URL: {invalid_urls}")
        print(f"  - Невалидных кодов: {invalid_codes}")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        print(f"\n✗ Ошибка загрузки: {e}")
