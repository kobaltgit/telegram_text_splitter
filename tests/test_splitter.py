# --- START OF FILE telegram_text_splitter/tests/test_splitter.py ---
import pytest
import logging

# Импортируем функцию, которую будем тестировать
from telegram_text_splitter import split_markdown_into_chunks

# Устанавливаем логгер для тестов, чтобы видеть предупреждения при необходимости
# Настроим уровень логгирования для тестирования
# logging.basicConfig(level=logging.WARNING) # Можно раскомментировать, если нужно видеть логи при тестах

# Определяем тестовый лимит, который меньше стандартного, для удобства тестирования
TEST_CHUNK_SIZE = 100 # Маленький размер для демонстрации разбиения

@pytest.fixture
def sample_markdown_text():
    """Предоставляет длинный Markdown текст для тестирования."""
    return """
# Пример текста для разбиения

Это первый абзац. Он содержит несколько строк и должен быть разделен.

## Второй раздел

*   Пункт списка 1
*   Пункт списка 2
    *   Вложенный пункт 2.1
    *   Вложенный пункт 2.2

Это абзац с очень длинным словом, которое может вызвать проблемы при разбивке: AntidisestablishmentarianismAntidisestablishmentarianismAntidisestablishmentarianismAntidisestablishmentarianismAntidisestablishmentarianismAntidisestablishmentarianism.

---

Конец документа.
"""

def test_split_markdown_into_chunks_basic(sample_markdown_text):
    """Тестирует базовое разбиение текста на чанки."""
    chunks = split_markdown_into_chunks(sample_markdown_text, max_chunk_size=TEST_CHUNK_SIZE)
    
    # Проверяем, что текст был разбит на несколько чанков
    assert len(chunks) > 1, "Текст не был разбит на несколько чанков."
    
    # Проверяем, что каждый чанк не превышает заданный лимит
    for i, chunk in enumerate(chunks):
        assert len(chunk) <= TEST_CHUNK_SIZE, f"Чанк {i+1} превышает лимит {TEST_CHUNK_SIZE} символов."
        print(f"\n--- Чанк {i+1} ({len(chunk)} символов) ---")
        print(chunk)
        print("-" * 20)

def test_split_markdown_empty_string():
    """Тестирует функцию с пустой строкой."""
    chunks = split_markdown_into_chunks("", max_chunk_size=TEST_CHUNK_SIZE)
    assert chunks == [], "Ожидался пустой список для пустой строки."

def test_split_markdown_short_string():
    """Тестирует функцию с короткой строкой, которая не требует разбиения."""
    short_text = "Это короткий текст."
    chunks = split_markdown_into_chunks(short_text, max_chunk_size=TEST_CHUNK_SIZE)
    assert len(chunks) == 1, "Ожидался один чанк для короткого текста."
    assert chunks[0] == short_text, "Содержимое чанка не совпадает с исходным коротким текстом."

def test_split_markdown_exact_limit():
    """Тестирует разбиение, когда текст точно равен лимиту."""
    text = "a" * TEST_CHUNK_SIZE
    chunks = split_markdown_into_chunks(text, max_chunk_size=TEST_CHUNK_SIZE)
    assert len(chunks) == 1, "Ожидался один чанк для текста точной длины лимита."
    assert len(chunks[0]) == TEST_CHUNK_SIZE, "Длина чанка не совпадает с лимитом."

def test_split_markdown_with_newlines(sample_markdown_text):
    """Тестирует разбиение с учетом переносов строк."""
    chunks = split_markdown_into_chunks(sample_markdown_text, max_chunk_size=TEST_CHUNK_SIZE)
    
    # Проверяем, что разбиение происходит по переносам, а не разрывает слова
    # (Это сложнее автоматизировать полностью, но мы проверим, что чанки заканчиваются на естественных разделителях)
    for chunk in chunks:
        # Проверяем, что чанк не обрывается посреди слова (простой эвристический тест)
        # Если чанк заканчивается на букву, а следующий начинается на букву, и нет пробела/переноса между ними,
        # это может указывать на проблему. Но проще проверять на естественных разделителях.
        if len(chunk) < TEST_CHUNK_SIZE: # Только для чанков, которые были точно разбиты
            last_char = chunk[-1]
            # Проверяем, что последний символ не является частью слова, которое будет продолжено
            # Если последний символ - буква, а следующий символ в полном тексте тоже буква (или цифра)
            # Это очень грубая проверка, но лучше, чем ничего.
            # Для более точных тестов нужно знать точное место разбиения и проверять окружающие символы.
            # Проще проверить, что чанки заканчиваются на естественные разделители.
            assert last_char in [' ', '\n', '\t'] or chunk.endswith('\n\n') or chunk.endswith('\n') or chunk.endswith(' '), \
                f"Чанк неожиданно закончился на: '{last_char}'. Возможно, разбиение произошло некорректно."

# Можно добавить больше тестов для специфичных случаев, например:
# - Текст с множеством HTML-тегов (хотя функция их не парсит, они влияют на длину)
# - Текст с очень длинными словами без пробелов
# - Текст, где разрыв строго по лимиту без естественного разделителя

# Запуск тестов:
# 1. Сохраните этот код как telegram_text_splitter_lib/tests/test_splitter.py
# 2. Сохраните pyproject.toml с добавленной секцией [project.optional-dependencies] и tool.pytest.ini_options
# 3. Установите библиотеку в режиме редактирования: cd telegram_text_splitter_lib && pip install -e .[test]
# 4. Запустите pytest из терминала в корневой папке проекта: pytest
# --- END OF FILE telegram_text_splitter/tests/test_splitter.py ---