import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

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

date_pattern = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")
green_phrases = ["имеется редакция, не вступившая в силу", "вступит в силу", "вступает в силу с"]
red_phrases = ["вносятся изменения", "акт изложен в новой редакции", "утратил силу"]

print("📘 Проверка кодексов на lex.uz\n")

for title, url in codes.items():
    try:
        r = requests.get(url)
        soup = BeautifulSoup(r.content, "html.parser")
        full_text = soup.get_text(separator=" ").lower()

        # Поиск даты
        dates = date_pattern.findall(full_text)
        parsed = [datetime.strptime(d, "%d.%m.%Y") for d in dates]
        latest = max(parsed).strftime("%d.%m.%Y") if parsed else "❌ не найдена"

        # Поиск заметок
        green_note = next((p for p in green_phrases if p in full_text), None)
        red_note = next((p for p in red_phrases if p in full_text), None)

        print(f"📘 {title}")
        print(f"🔗 {url}")
        print(f"🕒 Последняя дата изменения: {latest}")
        if green_note:
            print(f"🟩 Заметка: {green_note}")
        if red_note:
            print(f"🟥 Заметка: {red_note}")
        if not (green_note or red_note):
            print("ℹ️ Заметок нет")
        print("-" * 60)

    except Exception as e:
        print(f"❌ Ошибка с {title}: {e}")
