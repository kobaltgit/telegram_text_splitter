import logging
import re

logger = logging.getLogger(__name__)

# Максимальная длина сообщения в Telegram (4096 символов).
# Используем чуть меньше для запаса, чтобы избежать возможных проблем с краевыми случаями
# или если сама библиотека `chatgpt-md-converter` или Telegram добавит какой-то оверхед.
TELEGRAM_MESSAGE_LIMIT = 4000

def split_markdown_into_chunks(text: str, max_chunk_size: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """
    Разбивает длинный Markdown текст на более мелкие фрагменты, каждый из которых
    не превышает max_chunk_size. Старается разбивать по границам абзацев (\n\n),
    затем по строкам (\n), затем по словам (пробелы).
    
    Эта функция работает с чистым Markdown и не пытается парсить HTML, 
    что делает ее более надежной для последующей конвертации в HTML.

    :param text: Исходный длинный Markdown текст.
    :param max_chunk_size: Максимальный размер каждого фрагмента.
    :return: Список строк, представляющих фрагменты Markdown текста.
    """
    if not text:
        return []

    chunks = []
    current_pos = 0

    while current_pos < len(text):
        remaining_text = text[current_pos:]

        # Если оставшийся текст помещается целиком, добавляем его и завершаем
        if len(remaining_text) <= max_chunk_size:
            chunks.append(remaining_text)
            break
        
        # Определяем максимальную позицию для поиска разрыва, чтобы не выйти за лимит
        # Добавляем небольшой запас (+200) к max_chunk_size при поиске, чтобы найти разрыв
        # как можно ближе к границе, но не дальше нее.
        search_limit_index = min(len(remaining_text), max_chunk_size + 200) 
        search_slice = remaining_text[:search_limit_index]
        
        # Ищем точку разбиения, начиная с конца нашего диапазона поиска (ближе к max_chunk_size)
        break_point = -1 # Индекс в remaining_text, где будем разрывать

        # 1. Приоритет: двойной перенос строки (конец абзаца)
        # Ищем с конца, чтобы найти ближайший к max_chunk_size разрыв
        for i in range(min(len(search_slice) - 1, max_chunk_size), 0, -1):
            if search_slice[i:i+2] == "\n\n":
                break_point = i + 2 # Разделяем ПОСЛЕ \n\n, чтобы \n\n попали в предыдущий чанк
                break
        
        if break_point != -1:
            chunk = remaining_text[:break_point]
            chunks.append(chunk)
            current_pos += len(chunk)
            continue # Переходим к следующей итерации

        # 2. Если двойной перенос не найден, ищем одинарный перенос строки
        for i in range(min(len(search_slice) - 1, max_chunk_size), 0, -1):
            if search_slice[i] == "\n":
                break_point = i + 1 # Разделяем ПОСЛЕ \n
                break
        
        if break_point != -1:
            chunk = remaining_text[:break_point]
            chunks.append(chunk)
            current_pos += len(chunk)
            continue

        # 3. Если переносы не найдены, ищем пробел
        for i in range(min(len(search_slice) - 1, max_chunk_size), 0, -1):
            if search_slice[i] == " ":
                break_point = i + 1 # Разделяем ПОСЛЕ пробела
                break
        
        if break_point != -1:
            chunk = remaining_text[:break_point]
            chunks.append(chunk)
            current_pos += len(chunk)
            continue

        # 4. Крайний случай: обрезаем строго по max_chunk_size, если нет подходящих разрывов
        # Это может произойти, например, если есть очень длинное слово или ссылка без пробелов.
        chunk = remaining_text[:max_chunk_size]
        chunks.append(chunk)
        current_pos += len(chunk)
        logger.warning(f"Markdown split forced at {current_pos} due to no natural break points found within limit.")

    logger.info(f"Markdown text split into {len(chunks)} chunks.")
    return chunks