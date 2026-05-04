# Обновление путей после реорганизации

## Что изменилось

Проект реорганизован для лучшей структуры:

### Новая структура
```
.
├── benchmarks/          # Скрипты тестирования (НОВОЕ)
│   ├── test_single_model.py
│   ├── compare_models.py
│   ├── compare_search_results.py
│   └── compare_prefix_impact.py
├── docs/                # Документация (НОВОЕ)
│   ├── MODEL_*.md
│   ├── *СРАВНЕНИЕ*.md
│   ├── FRIDA_PREFIX_USAGE.md
│   └── ... (все .md и .txt файлы)
├── services/            # Сервисы (без изменений)
├── models/              # Модели (без изменений)
├── utils/               # Утилиты (без изменений)
└── tests/               # Тесты (без изменений)
```

## Обновленные команды

### Старые команды → Новые команды

#### Тестирование моделей

**Было:**
```bash
python test_single_model.py intfloat/multilingual-e5-small cuda
python compare_models.py
python compare_search_results.py
python compare_prefix_impact.py
```

**Стало:**
```bash
python benchmarks/test_single_model.py intfloat/multilingual-e5-small cuda
python benchmarks/compare_models.py
python benchmarks/compare_search_results.py
python benchmarks/compare_prefix_impact.py
```

#### Документация

**Было:**
```bash
notepad MODEL_ALTERNATIVES_SUMMARY.md
notepad QUICK_MODEL_COMPARISON.md
```

**Стало:**
```bash
notepad docs/MODEL_ALTERNATIVES_SUMMARY.md
notepad docs/QUICK_MODEL_COMPARISON.md
```

## Основные команды остались без изменений

```bash
# Загрузка данных
python load_tnved.py tnved_full10_new.xlsx

# Поиск
python search_tnved.py "кофе в зернах"

# Тесты
pytest tests/ -v
```

## Скрипты обновлены

Все скрипты в `benchmarks/` обновлены для работы из новой директории:
- ✅ Добавлен правильный путь к модулям проекта
- ✅ Обновлены пути к config.yaml
- ✅ Работают из любой директории

## Документация

Вся документация перемещена в `docs/`:
- Руководства по моделям
- FAQ
- Отчеты
- Справочные материалы

Основной README.md остался в корне проекта.

## Быстрая справка

### Тестирование одной модели
```bash
python benchmarks/test_single_model.py intfloat/multilingual-e5-small cuda
```

### Сравнение всех моделей
```bash
python benchmarks/compare_models.py
```

### Документация
```bash
# Краткое резюме
notepad docs/MODEL_ALTERNATIVES_SUMMARY.md

# Быстрый старт
notepad docs/QUICK_MODEL_COMPARISON.md

# Шпаргалка команд
notepad docs/COMMANDS_CHEATSHEET.txt
```

## Примечание

Некоторые файлы документации могут содержать старые пути. Используйте пути из этого файла как актуальные.
