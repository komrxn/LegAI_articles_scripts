import os
import re
import requests
import subprocess
import shutil
from bs4 import BeautifulSoup
from datetime import datetime

# Словарь кодексов и их URL на lex.uz
codes = {
    "Гражданский кодекс p1": "https://lex.uz/ru/docs/111181",
    "Гражданский кодекс p2": "https://lex.uz/ru/docs/180550",
    "Уголовный кодекс": "https://lex.uz/ru/docs/111457",
    "Семейный кодекс": "https://lex.uz/ru/docs/104723",
    "Трудовой кодекс": "https://lex.uz/ru/docs/6257291",
    "Административный кодекс": "https://lex.uz/ru/docs/97661",
    "Бюджетный кодекс": "https://lex.uz/ru/docs/2304140",
    "Гражданский процессуальный кодекс": "https://lex.uz/ru/docs/3517334",
    "Конституция": "https://lex.uz/docs/35869",
    "Уголовно-исполнительный кодекс": "https://lex.uz/ru/docs/163627",
    "Таможенный кодекс": "https://lex.uz/ru/docs/2876352",
    "Экономический процессуальный кодекс": "https://lex.uz/ru/docs/3523895",
    "Жилищный кодекс": "https://lex.uz/ru/docs/106134",
    "Земельный кодекс": "https://lex.uz/ru/docs/149947",
    "Налоговый кодекс": "https://lex.uz/ru/docs/4674893",
    "Кодекс об административном судопроизводстве": "https://lex.uz/ru/docs/3527365"
}

# Названия на английском для сохранённых файлов
names_en = {
    "Гражданский кодекс p1": "Civil Code Part1",
    "Гражданский кодекс p2": "Civil Code Part2",
    "Уголовный кодекс": "Criminal Code",
    "Семейный кодекс": "Family Code",
    "Трудовой кодекс": "Labor Code",
    "Административный кодекс": "Administrative Code",
    "Бюджетный кодекс": "Budget Code",
    "Гражданский процессуальный кодекс": "Civil Procedure Code",
    "Конституция": "Constitution",
    "Уголовно-исполнительный кодекс": "Criminal-Executive Code",
    "Таможенный кодекс": "Customs Code",
    "Экономический процессуальный кодекс": "Economic Procedure Code",
    "Жилищный кодекс": "Housing Code",
    "Земельный кодекс": "Land Code",
    "Налоговый кодекс": "Tax Code",
    "Кодекс об административном судопроизводстве": "Administrative Court Procedure Code"
}

# Паттерны для поиска дат и заметок
date_pattern = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")
green_phrases = [
    "имеется редакция, не вступившая в силу",
    "вступит в силу",
    "вступает в силу с"
]
red_phrases = [
    "вносятся изменения",
    "акт изложен в новой редакции",
    "утратил силу"
]

# Папки для скачивания и конвертации
doc_dir = os.path.join('data', 'doc')
docx_dir = os.path.join('data', 'docx')
os.makedirs(doc_dir, exist_ok=True)
os.makedirs(docx_dir, exist_ok=True)

# Определяем доступный инструмент для конвертации на macOS и Linux
converter = (
    shutil.which('libreoffice') or
    shutil.which('soffice') or
    shutil.which('unoconv') or
    '/Applications/LibreOffice.app/Contents/MacOS/soffice'
)
if converter and os.path.exists(converter):
    tool_name = os.path.basename(converter)
    print(f"🔧 Используется конвертер: {tool_name}\n")
else:
    converter = None
    print("⚠️ Конвертер .doc -> .docx не найден. Пропуск конвертации.\n")

print("📘 Запуск обработки кодексов с lex.uz\n")

for title, url in codes.items():
    print(f"🔍 Обработка: {title}")
    try:
        # Запрос страницы и парсинг текста
        r = requests.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')
        text_lower = soup.get_text(separator=' ').lower()

        # Поиск и форматирование даты последнего изменения
        dates = date_pattern.findall(text_lower)
        parsed = [datetime.strptime(d, '%d.%m.%Y') for d in dates]
        latest = max(parsed).strftime('%d.%m.%Y') if parsed else 'unknown_date'

        # Поиск заметок об изменениях
        green_note = next((p for p in green_phrases if p in text_lower), None)
        red_note = next((p for p in red_phrases if p in text_lower), None)
        print(f"🕒 Последнее изменение: {latest}")
        if green_note:
            print(f"🟩 Заметка: {green_note}")
        if red_note:
            print(f"🟥 Заметка: {red_note}")
        if not (green_note or red_note):
            print("ℹ️ Заметок нет")

        # Ссылка на скачивание .doc и лог
        doc_url = f"{url}?type=doc"
        print(f"📥 Загружаем с: {doc_url}")

        # Скачиваем .doc файл
        slug = re.sub(r'[^0-9a-zA-Zа-яА-Я]+', '_', title).strip('_')
        doc_path = os.path.join(doc_dir, f"{slug}.doc")
        with requests.get(doc_url, stream=True) as r_doc:
            r_doc.raise_for_status()
            with open(doc_path, 'wb') as f:
                for chunk in r_doc.iter_content(8192):
                    f.write(chunk)
        print(f"✅ Скачан .doc: {doc_path}")

        # Конвертация и переименование в .docx
        if converter:
            try:
                # Конвертируем в docx
                cmd = ([converter, '--headless', '--convert-to', 'docx', '--outdir', docx_dir, doc_path]
                       if tool_name.lower() != 'unoconv'
                       else [converter, '-f', 'docx', '-o', docx_dir, doc_path])
                subprocess.run(cmd, check=True)

                # Переименование в английское имя + дату
                en_name = names_en.get(title, slug)
                new_filename = f"{en_name} {latest}.docx"
                old_docx = os.path.join(docx_dir, f"{slug}.docx")
                new_path = os.path.join(docx_dir, new_filename)
                os.replace(old_docx, new_path)
                print(f"✅ Сохранён .docx: {new_path}\n")
            except Exception as conv_err:
                print(f"❌ Ошибка конвертации {title}: {conv_err}\n")
        else:
            print(f"⚠️ Пропущена конвертация для {title}\n")

    except Exception as e:
        print(f"❌ Ошибка при обработке {title}: {e}\n")

    print('-' * 40)
