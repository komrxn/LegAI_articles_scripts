# EDIT - MAX_ARTICLES , input_file
 
import re
import os
import json
from docx import Document

# Ручная установка максимального номера статьи
MAX_ARTICLES = 348 # Edit everytime!!

# Аббревиатуры кодексов для суффиксов статей
CODE_ABBR = {
    "civil": "ГК РУз",
    "civil": "ГК РУз",
    "criminal": "УК РУз",
    "family": "СК РУз",
    "labor": "ТК РУз",
    "administrative": "АК РУз",
    "budget": "БК РУз",
    "civil procedure": "ГПК РУз",
    "constitution": "Конституции РУз",
    "criminal executive": "УИК РУз",
    "customs": "Таможенный К РУз",
    "economic procedural": "ЭПК РУз",
    "housing": "ЖК РУз",
    "land": "ЗК РУз",
    "tax": "НК РУз",
    "administrative procedure": "АПК РУз"
}

# Ключи для детекции по имени файла
EN_KEYS = {
    'civil': 'Civil code p1',
    'p2': 'Civil code p2',
    'criminal': 'criminal',
    'family': 'family',
    'labor': 'labor',
    'administrative': 'administrative',
    'budget': 'budget',
    'civil procedural': 'civil procedural',
    'constitution': 'constitution',
    'criminal executive': 'criminal executive',
    'customs': 'customs',
    'economic procedural': 'economic procedural',
    'housing': 'housing',
    'land': 'land',
    'tax': 'tax',
    'administrative procedure': 'administrative procedure',
}

# Словарь преобразования надстрочных цифр
SUPERSCRIPT_MAP = str.maketrans({
    '¹': '1', '²': '2', '³': '3', '⁰': '0',
    '⁴': '4', '⁵': '5', '⁶': '6', '⁷': '7',
    '⁸': '8', '⁹': '9'
})


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', '', name)


def detect_code(input_file: str) -> str:
    fname = os.path.basename(input_file).lower()
    for key, code in EN_KEYS.items():
        if key in fname:
            return code
    for code in CODE_ABBR.keys():
        if code.lower() in fname:
            return code
    return 'unknown'


def read_docx(input_file: str) -> str:
    """Читает весь текст из .docx как единый строковый файл"""
    if not input_file.lower().endswith('.docx'):
        raise RuntimeError("Поддерживаются только .docx файлы")
    doc = Document(input_file)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)


def fix_article_number(num_str: str) -> str:
    """Преобразует номера статей выше MAX_ARTICLES в формат base(part)"""
    val_str = num_str
    val = int(val_str)
    max_str = str(MAX_ARTICLES)
    len_max = len(max_str)
    if val <= MAX_ARTICLES:
        return val_str
    if len(val_str) == len_max:
        return f"{max_str}({val_str[-1]})"
    if len(val_str) == len_max + 1:
        prefix, last = val_str[:-1], val_str[-1]
        if int(prefix) <= MAX_ARTICLES:
            return f"{prefix}({last})"
        return f"{max_str}({val_str[-2:]})"
    return f"{max_str}({val_str[len_max:]})"


def segment_articles(text: str, abbr: str):
    """Разбивает текст на статьи с корректной обработкой частей"""
    # добавляем явный перенос перед каждым 'Статья'
    text = re.sub(r'(?m)^Статья', '\nСтатья', text)
    # шаблон: 'Статья' + номер + часть + точка(?) + тело до следующей статьи
    pattern = re.compile(
        r"(Статья)\s+(\d+)([\.\d¹²³⁰-⁹]*)\.?\s*(.*?)(?=\nСтатья|$)",
        flags=re.DOTALL
    )
    articles = []
    for m in pattern.finditer(text):
        raw = m.group(2)
        part_raw = m.group(3)
        body = m.group(4).strip().replace('\n', ' ')
        part_ascii = part_raw.translate(SUPERSCRIPT_MAP).strip('.')
        fixed = fix_article_number(raw)
        num = f"{fixed}({part_ascii})" if part_ascii else fixed
        header = f"Статья {num} {abbr}".strip()
        articles.append({'Номер': num, 'Заголовок': header, 'Текст': body})
    return articles


def process_file(input_file: str):
    raw_text = read_docx(input_file)
    code_name = detect_code(input_file)
    if code_name == 'unknown':
        raise RuntimeError(f"Не удалось определить кодекс: {input_file}")
    abbr = CODE_ABBR[code_name]

    print(f"Определён кодекс: {code_name}")
    print(f"Max articles (ручной): {MAX_ARTICLES}")

    arts = segment_articles(raw_text, abbr)
    out_dir = os.path.join('articles_base', sanitize_filename(code_name))
    os.makedirs(out_dir, exist_ok=True)
    meta = []
    for art in arts:
        fname = sanitize_filename(f"{art['Номер']}.txt") or 'NoNumber.txt'
        path = os.path.join(out_dir, fname)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"{art['Заголовок']}\n{art['Текст']}")
        print(f"Создан файл: {path}")
        meta.append({'law_type': code_name, 'article_number': art['Номер'], 'file_path': fname})
    meta_path = os.path.join(out_dir, 'metadata.json')
    with open(meta_path, 'w', encoding='utf-8') as mf:
        json.dump(meta, mf, ensure_ascii=False, indent=2)
    print(f"Метаданные сохранены: {meta_path}")
    print('Обработка завершена.')

if __name__ == '__main__':
    input_file = 'data/docx/Administrative Code Nov 4 2025.docx'
    process_file(input_file)
 
