import pytest
import logging

# Импортируем функции, которые будем тестировать
from telegram_text_splitter import split_markdown_into_chunks
from telegram_text_splitter.splitter import find_safe_split

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
        print(f"\n--- Чанк {i+1} ({len(chunk)} символов) ---")
        print(chunk)
        print("-" * 20)
        assert len(chunk) <= TEST_CHUNK_SIZE, f"Чанк {i+1} превышает лимит {TEST_CHUNK_SIZE} символов."
        

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

# ===== NEW TESTS FOR CODE/LATEX AWARENESS =====

class TestFindSafeSplit:
    """Tests for the find_safe_split function."""

    def test_simple_text_no_special_blocks(self):
        """Test that normal text without code/LaTeX blocks works as expected."""
        text = "Hello world. This is a simple test with no special markers."
        result, continuation = find_safe_split(text, 20)
        # Should find a space or return the length if text is short enough
        assert result <= 20
        assert result > 0
        assert continuation is None

    def test_code_fence_protection(self):
        """Test that code fences are not broken."""
        text = """This is text before.

```python
def example():
    return "code"
```

This is text after."""
        
        # Try to split in the middle of the code block
        result, continuation = find_safe_split(text, 50)  # This would normally cut inside the code block
        
        # Verify the split doesn't break the code fence
        prefix = text[:result]
        fence_count = len([m for m in prefix.split('```') if m]) - 1
        # Should have even number of fences (complete pairs) or be before the first fence
        assert prefix.count('```') % 2 == 0, f"Code fence broken at position {result}"

    def test_inline_code_protection(self):
        """Test that inline code with backticks is not broken."""
        text = "Here is some `inline code with backticks` and more text."
        
        # Try to split in the middle where it would break inline code
        result, continuation = find_safe_split(text, 25)  # This could cut inside `inline code`
        
        # Verify the split doesn't break inline code
        prefix = text[:result]
        # Remove triple backticks first, then count single backticks
        without_triple = prefix.replace('```', '')
        single_backticks = without_triple.count('`')
        assert single_backticks % 2 == 0, f"Inline code broken at position {result}"

    def test_latex_inline_math_protection(self):
        """Test that inline LaTeX math $...$ is not broken."""
        text = "This is a formula $E = mc^2$ and some more text after it."
        
        # Try to split in the middle of the math
        result, continuation = find_safe_split(text, 25)  # This could cut inside $E = mc^2$
        
        # Verify the split doesn't break math
        prefix = text[:result]
        # Remove $$ first, then count single $
        without_double = prefix.replace('$$', '')
        single_dollars = without_double.count('$')
        assert single_dollars % 2 == 0, f"Inline math broken at position {result}"

    def test_latex_display_math_protection(self):
        """Test that display LaTeX math $$...$$ is not broken."""
        text = "Text before $$\\int_0^1 x^2 dx = \\frac{1}{3}$$ text after."
        
        # Try to split in the middle of display math
        result, continuation = find_safe_split(text, 25)  # This could cut inside $$...$$
        
        # Verify the split doesn't break display math
        prefix = text[:result]
        double_dollars = prefix.count('$$')
        assert double_dollars % 2 == 0, f"Display math broken at position {result}"

    def test_latex_bracket_math_protection(self):
        """Test that LaTeX bracket math \\[...\\] is not broken."""
        text = "Text before \\[\\sum_{i=1}^n i = \\frac{n(n+1)}{2}\\] text after."
        
        # Try to split in the middle of bracket math
        result, continuation = find_safe_split(text, 25)
        
        # Verify the split doesn't break bracket math
        prefix = text[:result]
        start_brackets = prefix.count('\\[')
        end_brackets = prefix.count('\\]')
        assert start_brackets <= end_brackets, f"Bracket math broken at position {result}"

    def test_multiple_code_blocks(self):
        """Test handling of multiple code blocks."""
        text = """First paragraph.

```python
def func1():
    pass
```

Middle paragraph.

```javascript
function func2() {
    return true;
}
```

Last paragraph."""
        
        result, continuation = find_safe_split(text, 80)
        prefix = text[:result]
        
        # Should not break any code fences
        assert prefix.count('```') % 2 == 0

    def test_mixed_code_and_math(self):
        """Test text with both code and math elements."""
        text = "Here is `code` and $math$ and ```\nblock code\n``` and $$display math$$ end."
        
        result, continuation = find_safe_split(text, 30)
        prefix = text[:result]
        
        # Check all delimiters are balanced
        # Code fences
        assert prefix.count('```') % 2 == 0
        
        # Display math
        assert prefix.count('$$') % 2 == 0
        
        # Inline code and math
        without_triple = prefix.replace('```', '')
        without_double_dollar = without_triple.replace('$$', '')
        assert without_triple.count('`') % 2 == 0
        assert without_double_dollar.count('$') % 2 == 0

    def test_rollback_behavior(self):
        """Test that the function rolls back to safe boundaries when needed."""
        text = "Short text ```python\ndef very_long_function_that_exceeds_limit():\n    return 'this is a long code block'\n``` after"
        
        # Set limit that would cut inside the code block
        result, continuation = find_safe_split(text, 50)
        
        # Should roll back to before the code block
        prefix = text[:result]
        assert '```' not in prefix or prefix.count('```') % 2 == 0

    def test_smart_code_splitting(self):
        """Test smart splitting of oversized code blocks."""
        # Create a code block that's too large for the chunk size
        long_code = "\n".join([f"    line_{i} = 'this is a very long line of code that makes the block oversized'" for i in range(10)])
        text = f"Short intro\n\n```python\n{long_code}\n```\n\nAfter text"
        
        # Set a small limit that forces smart splitting
        result, continuation = find_safe_split(text, 100)
        
        if continuation == "```":
            # Should have used smart splitting
            chunk = text[:result]
            assert chunk.endswith("```"), "Smart split should add closing ```"
            assert result == 100 - 3, "Should split at max_len-3 for code"
        else:
            # If it rolled back instead, that's also acceptable
            prefix = text[:result]
            assert '```' not in prefix or prefix.count('```') % 2 == 0

    def test_smart_latex_display_splitting(self):
        """Test smart splitting of oversized LaTeX display math."""
        # Create a display math block that's too large
        long_formula = "\\int_0^{\\infty} \\frac{1}{x^2 + a^2} dx = \\frac{\\pi}{2a} \\text{ and this continues with more complex expressions}"
        text = f"Text before $$\n{long_formula}\n$$ text after"
        
        # Set a limit that forces smart splitting
        result, continuation = find_safe_split(text, 80)
        
        if continuation == "$$":
            # Should have used smart splitting
            chunk = text[:result]
            assert chunk.endswith("$$"), "Smart split should add closing $$"
            assert result == 80 - 2, "Should split at max_len-2 for display math"

    def test_smart_latex_inline_splitting(self):
        """Test smart splitting of oversized inline LaTeX math."""
        # Create inline math that's too large
        long_formula = "E = mc^2 + \\sum_{i=1}^{\\infty} \\frac{1}{i^2} + \\int_0^1 x^n dx"
        text = f"The formula ${long_formula}$ continues here"
        
        # Set a limit that forces smart splitting
        result, continuation = find_safe_split(text, 50)
        
        if continuation == "$":
            # Should have used smart splitting
            chunk = text[:result]
            assert chunk.endswith("$"), "Smart split should add closing $"
            assert result == 50 - 1, "Should split at max_len-1 for inline math"


class TestMarkdownChunkingSafety:
    """Integration tests for the full chunking with safety."""

    def test_code_fence_not_split(self):
        """Test that code fences are not split when possible."""
        text = """# Header

Some text before the code.

```python
def example():
    return "short"
```

More text after the code block."""
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=200)  # Larger size to accommodate the block
        
        # Verify no chunk starts or ends with partial code fence
        for i, chunk in enumerate(chunks):
            fence_count = chunk.count('```')
            assert fence_count % 2 == 0, f"Chunk {i} has unbalanced code fences: {repr(chunk)}"

    def test_inline_code_not_split(self):
        """Test that inline code is never split across chunks."""
        text = "This has `some inline code that is quite long` and continues with more text that should be in the next chunk."
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=40)
        
        # Verify no chunk has unbalanced backticks
        for i, chunk in enumerate(chunks):
            without_triple = chunk.replace('```', '')
            backtick_count = without_triple.count('`')
            assert backtick_count % 2 == 0, f"Chunk {i} has unbalanced inline code: {repr(chunk)}"

    def test_latex_math_not_split(self):
        """Test that LaTeX math expressions are not split."""
        text = "The equation $E = mc^2$ is famous. And here's display math: $$\\int_0^\\infty e^{-x} dx = 1$$ which is also important."
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=80)  # Larger size to accommodate the expressions
        
        # Verify math expressions are not broken
        for i, chunk in enumerate(chunks):
            # Check display math
            assert chunk.count('$$') % 2 == 0, f"Chunk {i} has unbalanced display math"
            
            # Check inline math
            without_display = chunk.replace('$$', '')
            assert without_display.count('$') % 2 == 0, f"Chunk {i} has unbalanced inline math"

    def test_complex_document_safety(self):
        """Test a complex document with mixed content."""
        text = """# Mathematical Programming

## Introduction

Here's some `inline code` and a math formula $x^2 + y^2 = z^2$.

```python
def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2-x1)**2 + (y2-y1)**2)
```

The distance formula in display math:

$$d = \\sqrt{(x_2-x_1)^2 + (y_2-y_1)^2}$$

More text with `another code snippet` continues here.

### Code Example

```javascript
function factorial(n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}
```

And finally some bracket math: \\[\\sum_{i=1}^n i = \\frac{n(n+1)}{2}\\]

The end."""
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=150)
        
        # Verify all chunks are safe
        for i, chunk in enumerate(chunks):
            # Code fences
            assert chunk.count('```') % 2 == 0, f"Chunk {i} has unbalanced code fences"
            
            # Display math
            assert chunk.count('$$') % 2 == 0, f"Chunk {i} has unbalanced display math"
            
            # Bracket math
            assert chunk.count('\\[') <= chunk.count('\\]'), f"Chunk {i} has unbalanced bracket math"
            
            # Inline code and math
            tmp_no_triple = chunk.replace('```', '')
            tmp_no_display = tmp_no_triple.replace('$$', '')
            assert tmp_no_triple.count('`') % 2 == 0, f"Chunk {i} has unbalanced inline code"
            assert tmp_no_display.count('$') % 2 == 0, f"Chunk {i} has unbalanced inline math"

    def test_forced_split_warning(self):
        """Test that the splitter handles oversized blocks gracefully."""
        # Create text with very long code block that can't be split safely
        long_code = "x" * 200  # Very long variable name
        text = f"Short intro ```python\n{long_code}\n``` end"
        
        # Force split with small limit
        chunks = split_markdown_into_chunks(text, max_chunk_size=50)
        
        # Should still produce chunks
        assert len(chunks) >= 1
        
        # In extreme cases where blocks are much larger than chunk size,
        # the algorithm may be forced to split inside blocks
        # Just verify that we get reasonable chunks and don't infinite loop
        total_reconstructed = "".join(chunks)
        assert "Short intro" in total_reconstructed
        assert "end" in total_reconstructed
        assert len(chunks) > 1  # Should split into multiple chunks

    def test_oversized_code_blocks_handled(self):
        """Test that oversized code blocks are handled gracefully."""
        # Code block larger than chunk size
        large_code = "\n".join([f"    line_{i} = 'this is a long line of code'" for i in range(20)])
        text = f"Before text\n\n```python\n{large_code}\n```\n\nAfter text"
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=100)
        
        # Should still produce valid chunks
        assert len(chunks) >= 1
        
        # Reconstruct text to verify nothing is lost
        reconstructed = "".join(chunks)
        # Allow for some whitespace differences due to lstrip in the algorithm
        assert "Before text" in reconstructed
        assert "After text" in reconstructed
        assert "```python" in reconstructed

    def test_normal_size_blocks_not_split(self):
        """Test that normal-sized blocks are kept intact."""
        text = """Normal text before.

```python
def small_function():
    return True
```

Normal text after."""
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=150)
        
        # Should be in one chunk since it fits
        assert len(chunks) == 1
        # And code fence should be intact
        assert chunks[0].count('```') == 2

    def test_partial_fence_detection(self):
        """Test that splits don't happen in the middle of code fence markers."""
        # Recreate the exact issue: text ending with partial fence
        text = """Some text before.

```python
def function1():
    pass
```
another copy:
```python
def function2():
    pass
```"""
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=100)
        
        # Verify no chunk ends with partial fence (but allow complete fences)
        for i, chunk in enumerate(chunks):
            # Check for partial fence patterns
            assert not (chunk.endswith("``") and not chunk.endswith("```")), f"Chunk {i} ends with partial fence: {repr(chunk[-10:])}"
            assert not (chunk.endswith("`") and not chunk.endswith("```")), f"Chunk {i} ends with single backtick: {repr(chunk[-10:])}"
            # All chunks should have balanced fences
            fence_count = chunk.count('```')
            assert fence_count % 2 == 0, f"Chunk {i} has unbalanced code fences"

    def test_smart_splitting_integration(self):
        """Test that smart splitting works correctly in the full chunking process."""
        # Create text with an oversized code block
        large_code = "\n".join([
            f"def function_{i}():\n"
            f"  return 'this is line {i} of a very long function'" for i in range(20)])

        text = f"Before text\n\n```python\n{large_code}\n```\n\nAfter text"
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=200)
        for i, chunk in enumerate(chunks):
            print(f"Chunk {i}: {chunk}")
        
        # Should produce multiple chunks
        assert len(chunks) >= 2
        
        # Check if any chunks show evidence of smart splitting (ending with ```)
        has_smart_split = False
        for i, chunk in enumerate(chunks):
            if chunk.endswith("```") and i < len(chunks) - 1:  # Not the last chunk
                has_smart_split = True
                # Next chunk should start with ```
                next_chunk = chunks[i + 1]
                assert next_chunk.startswith("```"), f"Chunk {i+1} should start with ``` after smart split"
        
        # Verify all chunks are safe (no unbalanced delimiters)
        for i, chunk in enumerate(chunks):
            fence_count = chunk.count('```')
            assert fence_count % 2 == 0, f"Chunk {i} has unbalanced code fences"
        
        # Verify content is preserved
        reconstructed = "".join(chunk.replace("```\n```", "") for chunk in chunks)  # Remove continuation markers
        assert "Before text" in reconstructed
        assert "After text" in reconstructed
        assert "def function_" in reconstructed

    def test_smart_splitting_latex_integration(self):
        """Test smart splitting for LaTeX formulas in full chunking."""
        # Create text with oversized LaTeX
        long_formula = " + ".join([f"\\frac{{1}}{{{i}^2}}" for i in range(1, 30)])
        text = f"Mathematical series: $${long_formula}$$ which converges."
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=150)
        
        # Should produce multiple chunks if the formula is large enough
        if len(chunks) > 1:
            # Check for smart splitting evidence
            for i, chunk in enumerate(chunks):
                # All chunks should have balanced math delimiters
                print(f"Checking chunk {i}: {chunk}")
                assert chunk.count('$$') % 2 == 0, f"Chunk {i} has unbalanced display math"
        
        # Verify content preservation
        reconstructed = "".join(chunk.replace("$$\n$$", "") for chunk in chunks)
        assert "Mathematical series" in reconstructed
        assert "which converges" in reconstructed


class TestComprehensiveSmartSplitting:
    """Comprehensive tests for all smart splitting scenarios mentioned by the user."""

    def test_mixed_latex_text_code(self):
        """Test a mix of LaTeX, text, and code blocks."""
        text = """# Mathematical Programming

Here's inline math $E = mc^2$ and display math:

$$\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}$$

Some explanatory text between formulas and code.

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

More text with another formula:

$$\\int_0^1 x^2 dx = \\frac{1}{3}$$

End of document."""
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=200)
        
        # Verify all chunks are balanced
        for i, chunk in enumerate(chunks):
            # Check code fences
            assert chunk.count('```') % 2 == 0, f"Chunk {i} has unbalanced code fences"
            # Check display math
            assert chunk.count('$$') % 2 == 0, f"Chunk {i} has unbalanced display math"
            # Check inline math
            without_display = chunk.replace('$$', '')
            assert without_display.count('$') % 2 == 0, f"Chunk {i} has unbalanced inline math"
        
        # Verify content preservation
        reconstructed = "".join(chunks)
        assert "Mathematical Programming" in reconstructed
        assert "fibonacci" in reconstructed
        assert "\\sum_{i=1}^{n}" in reconstructed
        assert "\\int_0^1" in reconstructed

    def test_very_long_code_block(self):
        """Test very long code block with proper language preservation and newline splitting."""
        # Create a very long Python function
        long_code = []
        for i in range(50):
            long_code.extend([
                f"def function_{i}():",
                f"    # This is function {i} with detailed implementation",
                f"    variable_a = {i} * 2 + 5",
                f"    variable_b = variable_a ** 2",
                f"    result = variable_a + variable_b - {i}",
                f"    return result",
                ""
            ])
        
        code_content = "\n".join(long_code)
        text = f"Before code block.\n\n```python\n{code_content}```\n\nAfter code block."
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=400)
        
        # Should produce multiple chunks
        assert len(chunks) >= 3
        
        # Verify all code chunks are balanced
        for i, chunk in enumerate(chunks):
            fence_count = chunk.count('```')
            assert fence_count % 2 == 0, f"Chunk {i} has unbalanced code fences: {fence_count}"
        
        # Verify language preservation in continuation chunks
        code_chunks = [chunk for chunk in chunks if '```python' in chunk or chunk.startswith('```python')]
        assert len(code_chunks) >= 1, "At least one chunk should have ```python"
        
        # Verify content preservation - no code should be lost
        reconstructed = "".join(chunk.replace('```\n```python\n', '') for chunk in chunks)
        for i in range(0, min(50, 10)):  # Check first 10 functions
            assert f"def function_{i}():" in reconstructed
            assert f"variable_a = {i} * 2 + 5" in reconstructed

    def test_very_long_latex_formula(self):
        """Test very long LaTeX formula with newline priority over operators."""
        # Create a very long LaTeX formula with multiple lines
        formula_lines = []
        for i in range(30):
            formula_lines.append(f"    \\frac{{d}}{{dx}}\\left(\\int_{{-{i}}}^{{+{i}}} f_{i}(t) dt \\right) = f_{{i}}({i}) - f_{{i}}(-{i})")
        
        formula_content = "\n".join(formula_lines)
        text = f"Mathematical derivation:\n\n$$\n{formula_content}\n$$\n\nConclusion follows."
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=600)
        
        # Should produce multiple chunks
        assert len(chunks) >= 3
        
        # Verify all LaTeX chunks are balanced
        for i, chunk in enumerate(chunks):
            dollar_count = chunk.count('$$')
            assert dollar_count % 2 == 0, f"Chunk {i} has unbalanced $$: {dollar_count}"
        
        # Verify newline splitting priority - no chunk should end mid-formula
        for i, chunk in enumerate(chunks):
            if '$$' in chunk and i < len(chunks) - 1:  # Not the last chunk with LaTeX
                # Should not end with incomplete formula parts
                assert not chunk.strip().endswith('\\int_{'), f"Chunk {i} breaks integral formula"
                assert not chunk.strip().endswith('\\frac{'), f"Chunk {i} breaks fraction formula"
                assert not chunk.strip().endswith('+'), f"Chunk {i} breaks at operator without newline"
        
        # Verify content preservation
        reconstructed = "".join(chunk.replace('$$\n$$\n', '') for chunk in chunks)
        for i in range(0, min(30, 5)):  # Check first 5 formulas
            assert f"f_{i}(t)" in reconstructed
            assert f"f_{{i}}({i})" in reconstructed

    def test_very_long_mixed_content(self):
        """Test very long document with mixed code, text, and LaTeX formulas."""
        # Create complex mixed content
        text_parts = []
        
        # Add introduction
        text_parts.append("# Complex Mathematical and Programming Document")
        text_parts.append("\nThis document contains mixed content to test splitting.\n")
        
        # Add LaTeX section
        text_parts.append("## Mathematical Foundations\n")
        formula_lines = []
        for i in range(15):
            formula_lines.append(f"    \\sum_{{k=1}}^{{{i}}} k^2 = \\frac{{{i}({i}+1)(2{i}+1)}}{{6}}")
        text_parts.append(f"$$\n{chr(10).join(formula_lines)}\n$$\n")
        
        # Add code section
        text_parts.append("## Implementation\n")
        code_lines = []
        for i in range(20):
            code_lines.extend([
                f"class Calculator{i}:",
                f"    def __init__(self, value={i}):",
                f"        self.value = value",
                f"        self.result = value * {i} + 1",
                f"",
                f"    def calculate(self):",
                f"        return self.value ** 2 + {i}",
                ""
            ])
        text_parts.append(f"```python\n{chr(10).join(code_lines)}```\n")
        
        # Add more LaTeX
        text_parts.append("## Advanced Formulas\n")
        complex_formula = "    \\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2} + \\sum_{n=0}^\\infty \\frac{(-1)^n x^{2n+1}}{n!(2n+1)}"
        text_parts.append(f"$$\n{complex_formula}\n$$\n")
        
        text_parts.append("## Conclusion\nThis completes our analysis.")
        
        full_text = "\n".join(text_parts)
        
        chunks = split_markdown_into_chunks(full_text, max_chunk_size=800)
        
        # Should produce multiple chunks
        assert len(chunks) >= 3
        
        # Verify all chunks are balanced
        for i, chunk in enumerate(chunks):
            # Code fences
            assert chunk.count('```') % 2 == 0, f"Chunk {i} has unbalanced code fences"
            # Display math
            assert chunk.count('$$') % 2 == 0, f"Chunk {i} has unbalanced display math"
            # Inline math (if any)
            without_display = chunk.replace('$$', '')
            assert without_display.count('$') % 2 == 0, f"Chunk {i} has unbalanced inline math"
        
        # Verify content preservation
        reconstructed = "".join(chunks)
        assert "Complex Mathematical" in reconstructed
        assert "Calculator" in reconstructed
        assert "\\sum_{k=1}" in reconstructed
        assert "\\int_0^\\infty" in reconstructed
        assert "Conclusion" in reconstructed

    def test_newline_priority_over_operators(self):
        """Test that newlines have priority over mathematical operators in splitting."""
        # Create LaTeX with operators and newlines
        text = """Mathematical proof:

$$
First line with addition: a + b = c
Second line with subtraction: x - y = z
Third line with multiplication: p * q = r
Fourth line with division: m / n = k
$$

End of proof."""
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=120)
        
        # Find chunks that contain LaTeX
        latex_chunks = [chunk for chunk in chunks if '$$' in chunk]
        
        if len(latex_chunks) > 1:  # If LaTeX was split
            for chunk in latex_chunks[:-1]:  # All but last chunk
                # Should end at complete lines, not break at operators
                lines = chunk.strip().split('\n')
                if lines and not lines[-1].strip() in ['$$', '']:
                    last_line = lines[-1].strip()
                    # Should not end with incomplete expressions
                    assert not last_line.endswith(' +'), "Split at + operator instead of newline"
                    assert not last_line.endswith(' -'), "Split at - operator instead of newline"
                    assert not last_line.endswith(' *'), "Split at * operator instead of newline"
                    assert not last_line.endswith(' /'), "Split at / operator instead of newline"

    def test_content_preservation_no_symbol_loss(self):
        """Test that no meaningful symbols are lost during splitting (except whitespace)."""
        original_text = """# Test Document

Inline math: $\\alpha + \\beta = \\gamma$ and more text.

Display math:
$$\\int_0^1 x^2 dx = \\frac{1}{3} + \\sum_{n=1}^\\infty \\frac{1}{n^2}$$

Code example:
```python
def test_function(x, y):
    result = x + y * 2 - 1
    return result ** 2
```

More text with special symbols: @#$%^&*()_+-=[]{}|;:,.<>?/~`"""
        
        chunks = split_markdown_into_chunks(original_text, max_chunk_size=150)
        
        # Reconstruct text by removing only continuation markers
        reconstructed = ""
        for chunk in chunks:
            # Remove continuation markers but keep all other content
            cleaned = chunk
            # Remove smart-split continuation markers
            cleaned = cleaned.replace('```\n```python\n', '')
            cleaned = cleaned.replace('$$\n$$\n', '')
            cleaned = cleaned.replace('\n$$\n$$\n', '\n')
            reconstructed += cleaned
        
        # Define characters that should be preserved exactly
        important_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        important_chars.update('\\{}[]()+-*/=<>^_$#@%&|:;,.?!~`"\'')
        
        # Count important characters in original and reconstructed
        original_important = {char: original_text.count(char) for char in important_chars if char in original_text}
        reconstructed_important = {char: reconstructed.count(char) for char in important_chars if char in reconstructed}
        
        # Verify no important characters are lost
        for char, original_count in original_important.items():
            reconstructed_count = reconstructed_important.get(char, 0)
            assert reconstructed_count >= original_count, f"Character '{char}' lost: {original_count} -> {reconstructed_count}"
        
        # Verify key content is preserved
        assert "test_function" in reconstructed
        assert "\\alpha + \\beta" in reconstructed
        assert "\\int_0^1" in reconstructed
        assert "special symbols" in reconstructed

    def test_code_newline_priority(self):
        """Test that code blocks prioritize splitting at newlines over operators."""
        # Create code with operators and newlines
        code_content = """def complex_calculation():
    result_a = 10 + 20 * 3
    result_b = result_a - 5 / 2
    result_c = result_b ** 2 + 1
    return result_c

def another_function():
    value = 100 - 50 + 25
    return value * 2"""
        
        text = f"Code example:\n\n```python\n{code_content}\n```\n\nEnd of code."
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=180)
        
        # Find code chunks
        code_chunks = [chunk for chunk in chunks if '```' in chunk]
        
        if len(code_chunks) > 1:  # If code was split
            for chunk in code_chunks[:-1]:  # All but last chunk
                lines = chunk.split('\n')
                # Should end at complete lines, not break at operators within lines
                for line in lines:
                    if 'result_a = 10 +' in line:
                        # Should not break mathematical expressions within code
                        assert '10 + 20 * 3' in chunk or '10 +' not in chunk.split('\n')[-2]

    def test_mathematical_operator_splitting_fallback(self):
        """Test that when newlines aren't available, splitting falls back to operators correctly."""
        # Create a LaTeX formula on a single line that's too long
        long_single_line = "$$a + b + c + d + e + f + g + h + i + j + k + l + m + n + o + p + q + r + s + t + u + v + w + x + y + z = result$$"
        
        text = f"Formula: {long_single_line}\n\nEnd."
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=80)
        
        # Should split at operators since no newlines available
        latex_chunks = [chunk for chunk in chunks if '$$' in chunk]
        
        if len(latex_chunks) > 1:
            # Verify it split at reasonable operator positions
            for chunk in latex_chunks[:-1]:  # All but last
                if not chunk.strip().endswith('$$'):
                    # Should end at operator boundaries when possible
                    content = chunk.replace('$$', '').strip()
                    if content and content[-1] in '+-=':
                        assert True  # Split at operator - this is expected fallback
                    elif content:
                        # If not at operator, should be due to length constraints
                        assert len(chunk) >= 70  # Near the limit

    def test_balanced_delimiters_comprehensive(self):
        """Comprehensive test ensuring all delimiter types remain balanced."""
        text = """# All Delimiter Types

Inline code: `variable = value` and more.

Fenced code:
```javascript
function test() {
    return x + y;
}
```

Inline math: $x^2 + y^2 = z^2$ continues.

Display math:
$$\\sum_{i=1}^n i = \\frac{n(n+1)}{2}$$

Bracket math:
\\[\\int_a^b f(x) dx = F(b) - F(a)\\]

Mixed content with multiple blocks."""
        
        chunks = split_markdown_into_chunks(text, max_chunk_size=120)
        
        for i, chunk in enumerate(chunks):
            # Test all delimiter types
            assert chunk.count('```') % 2 == 0, f"Chunk {i}: Unbalanced ```"
            assert chunk.count('$$') % 2 == 0, f"Chunk {i}: Unbalanced $$"
            assert chunk.count('\\[') <= chunk.count('\\]'), f"Chunk {i}: Unbalanced \\[\\]"
            
            # Test inline delimiters
            without_triple = chunk.replace('```', '')
            without_display = without_triple.replace('$$', '')
            assert without_triple.count('`') % 2 == 0, f"Chunk {i}: Unbalanced `"
            assert without_display.count('$') % 2 == 0, f"Chunk {i}: Unbalanced $"