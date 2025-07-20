# Изменения: 
# MAX_ARTICLES
# law_type
# "... РУз"
# input_file

import re
import os
import json

MAX_ARTICLES = 1199

def fix_article_number(num_str):
    """Форматирует номер статьи для Уголовного кодекса."""
    try:
        num_val = int(num_str)
        if num_val <= MAX_ARTICLES:
            return num_str
        else:
            last_digit = num_str[-1]
            rest = num_str[:-1]
            return f"{rest}({last_digit})"
    except ValueError:
        return num_str

def segment_articles(text):
    """Делит текст на статьи."""
    article_pattern = r"(Статья\s+\d+\.?\s+.*?)(?=\nСтатья\s+\d+\.?\s+|$)"
    blocks = re.findall(article_pattern, text, flags=re.DOTALL|re.IGNORECASE)
    articles = []
    
    for block in blocks:
        block = block.strip()
        lines = block.split("\n")
        if not lines:
            continue
        
        article_header = lines[0].strip()
        article_body = " ".join(line.strip() for line in lines[1:] if line.strip())
        
        num_match = re.search(r"Статья\s+(\d+)", article_header, flags=re.IGNORECASE)
        if num_match:
            raw_num = num_match.group(1)
            new_num = fix_article_number(raw_num)
            
            # Используем функцию для замены
            def repl_func(m):
                return f"{m.group(1)}{new_num} ГК РУз{m.group(2)}"
            
            pattern_replace = rf"(Статья\s+){raw_num}(\.?)"
            article_header_modified = re.sub(pattern_replace, repl_func, article_header, flags=re.IGNORECASE)
            article_number = new_num
        else:
            article_header_modified = article_header
            article_number = ""
        
        articles.append({
            "Номер": article_number,
            "Заголовок": article_header_modified,
            "Текст": article_body
        })
    return articles

def read_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def segment_chapters(text):
    """Делит текст на главы."""
    chapter_pattern = r"(ГЛАВА\s+(?:[IVXLCDM]+|\d+)\s*[^\n\r]*)"
    parts = re.split(chapter_pattern, text, flags=re.IGNORECASE)
    chapters = []
    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            chapter_title = parts[i].strip()
            chapter_text = parts[i+1] if i+1 < len(parts) else ""
            chapters.append({"Название": chapter_title, "Текст": chapter_text})
    else:
        chapters.append({"Название": "Единая глава", "Текст": text})
    return chapters

def process_file(input_file, output_dir):
    """Обрабатывает файл, создаёт файлы статей и метаданные."""
    text = read_txt(input_file)
    
    # Определяем тип закона
    filename_lower = os.path.basename(input_file).lower()
    if "сivil" in filename_lower:
        law_type = "сivil"
    elif "criminal" in filename_lower:
        law_type = "criminal"
    else:
        law_type = "unknown"
    print(f"Определён тип закона: {law_type}")
    
    text = text.replace("ГЛАВА", "\nГЛАВА").replace("Статья", "\nСтатья")
    chapters = segment_chapters(text)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    metadata = []
    
    for chapter in chapters:
        chapter_title = chapter["Название"]
        chapter_text = chapter["Текст"]
        match = re.search(r"ГЛАВА\s+([IVXLCDM]+|\d+)", chapter_title, re.IGNORECASE)
        chapter_number = int(match.group(1)) if match and match.group(1).isdigit() else 0
        
        articles = segment_articles(chapter_text)
        
        for article in articles:
            article_num = article["Номер"]
            article_header = article["Заголовок"]
            article_body = article["Текст"]
            
            filename = f"{article_num}.txt" if article_num else "NoNumber.txt"
            filename = sanitize_filename(filename)
            file_path = os.path.join(output_dir, filename)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"Глава: {chapter_title}\n\n{article_header}\n\n{article_body}\n")
            print(f"Создан файл: {file_path}")
            
            metadata.append({
                "law_type": law_type,
                "article_number": article_num,
                "article_title_number": chapter_number,
                "file_path": filename
            })
    
    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"Создан файл метаданных: {metadata_path}")
    print("Обработка завершена.")

if __name__ == "__main__":
    input_file = "data/text/Civil Code UZ.txt"
    output_dir = "articles_base/Civil Code_metadata"
    process_file(input_file, output_dir)