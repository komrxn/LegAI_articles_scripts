#!/usr/bin/env python3
"""Universal lex.uz law parser - extracts articles from downloaded HTML pages."""

import json
import re
import sys
import time
from pathlib import Path
from dataclasses import dataclass
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from bs4 import BeautifulSoup

# ═══════════════════════════════════════════════════════════════════════════════
# ANSI Colors & Styles
# ═══════════════════════════════════════════════════════════════════════════════
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"

def log_info(msg): print(f"  {C.CYAN}ℹ{C.RESET}  {msg}")
def log_success(msg): print(f"  {C.GREEN}✓{C.RESET}  {msg}")
def log_error(msg): print(f"  {C.RED}✗{C.RESET}  {C.RED}{msg}{C.RESET}")
def log_warn(msg): print(f"  {C.YELLOW}⚠{C.RESET}  {C.YELLOW}{msg}{C.RESET}")

def banner():
    print(f"""
{C.CYAN}{C.BOLD}╔═══════════════════════════════════════════════════════════╗
║             🏛️  LEX.UZ LAW PARSER  🏛️                      ║
║         Universal Uzbekistan Legal Code Extractor          ║
╚═══════════════════════════════════════════════════════════╝{C.RESET}
""")

def progress_bar(current, total, width=40, prefix=""):
    pct = current / total
    filled = int(width * pct)
    bar = f"{C.GREEN}{'█' * filled}{C.DIM}{'░' * (width - filled)}{C.RESET}"
    sys.stdout.write(f"\r  {prefix} [{bar}] {C.BOLD}{current}/{total}{C.RESET} ")
    sys.stdout.flush()
    if current == total:
        print()

# ═══════════════════════════════════════════════════════════════════════════════
# Code Registry (ID → folder, abbreviation, full name, URL)
# ═══════════════════════════════════════════════════════════════════════════════
CODES = {
    "111181":  ("civil_p1",              "ГК РУз",           "Гражданский кодекс (ч.1)",           "https://lex.uz/ru/docs/111181"),
    "180550":  ("civil_p2",              "ГК РУз",           "Гражданский кодекс (ч.2)",           "https://lex.uz/ru/docs/180550"),
    "111457":  ("criminal",              "УК РУз",           "Уголовный кодекс",                   "https://lex.uz/ru/docs/111457"),
    "104723":  ("family",                "СК РУз",           "Семейный кодекс",                    "https://lex.uz/ru/docs/104723"),
    "6257291": ("labor",                 "ТК РУз",           "Трудовой кодекс",                    "https://lex.uz/ru/docs/6257291"),
    "97661":   ("administrative",        "КоАО РУз",         "Административный кодекс",            "https://lex.uz/ru/docs/97661"),
    "2304140": ("budget",                "БК РУз",           "Бюджетный кодекс",                   "https://lex.uz/ru/docs/2304140"),
    "3517334": ("civil_procedure",       "ГПК РУз",          "Гражданский процессуальный",         "https://lex.uz/ru/docs/3517334"),
    "6445147": ("constitution",          "Конституция РУз",  "Конституция",                        "https://lex.uz/docs/6445147"),
    "163627":  ("criminal_executive",    "УИК РУз",          "Уголовно-исполнительный",            "https://lex.uz/ru/docs/163627"),
    "2876352": ("customs",               "ТамК РУз",         "Таможенный кодекс",                  "https://lex.uz/ru/docs/2876352"),
    "3523895": ("economic_procedure",    "ЭПК РУз",          "Экономический процессуальный",       "https://lex.uz/ru/docs/3523895"),
    "106134":  ("housing",               "ЖК РУз",           "Жилищный кодекс",                    "https://lex.uz/ru/docs/106134"),
    "149947":  ("land",                  "ЗК РУз",           "Земельный кодекс",                   "https://lex.uz/ru/docs/149947"),
    "4674893": ("tax",                   "НК РУз",           "Налоговый кодекс",                   "https://lex.uz/ru/docs/4674893"),
    "3527365": ("administrative_procedure", "АПК РУз",       "Админ. судопроизводство",            "https://lex.uz/ru/docs/3527365"),
}

# Output directory: ../codes relative to this script
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / "codes"
CACHE_DIR = SCRIPT_DIR / ".cache"

# ═══════════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class Article:
    number: str
    title: str
    text: str

# ═══════════════════════════════════════════════════════════════════════════════
# Downloader
# ═══════════════════════════════════════════════════════════════════════════════
def download_page(code_id: str) -> str:
    """Download HTML page from lex.uz"""
    if code_id not in CODES:
        raise ValueError(f"Unknown code: {code_id}")
    
    _, _, name, url = CODES[code_id]
    
    # Check cache first
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / code_id
    if cache_file.exists():
        log_info(f"Загружаю из кэша: {C.DIM}{code_id}{C.RESET}")
        return cache_file.read_text(encoding="utf-8")
    
    log_info(f"Скачиваю {C.BOLD}{name}{C.RESET}...")
    log_info(f"{C.DIM}{url}{C.RESET}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8")
        
        # Cache for future use
        cache_file.write_text(html, encoding="utf-8")
        log_success("Скачано и закэшировано")
        return html
        
    except HTTPError as e:
        raise RuntimeError(f"HTTP ошибка {e.code}: {e.reason}")
    except URLError as e:
        raise RuntimeError(f"Ошибка сети: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Ошибка загрузки: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# Parser Core
# ═══════════════════════════════════════════════════════════════════════════════
def extract_article_number(prefix_span) -> str | None:
    """Extract article number, converting <sup> to parentheses: 26<sup>1</sup> → 26(1)"""
    for sup in prefix_span.find_all("sup"):
        sup.replace_with(f"({sup.get_text()})")
    text = prefix_span.get_text()
    match = re.search(r"Статья\s+([\d\(\)]+)", text)
    return match.group(1) if match else None


def extract_articles(html: str, show_progress=True) -> list[Article]:
    """Parse HTML and extract all articles."""
    log_info("Парсинг HTML...")
    soup = BeautifulSoup(html, "html.parser")
    clauses = soup.find_all("div", class_="CLAUSE_DEFAULT")
    
    if not clauses:
        return []
    
    log_info(f"Найдено {C.BOLD}{len(clauses)}{C.RESET} статей, извлекаю...")
    articles = []
    
    for i, clause in enumerate(clauses):
        if show_progress:
            progress_bar(i + 1, len(clauses), prefix="Обработка")
        
        prefix = clause.find("span", class_="clausePrfx")
        if not prefix:
            continue
        
        number = extract_article_number(prefix)
        if not number:
            continue
        
        suffix = clause.find("span", class_="clauseSuff")
        title = suffix.get_text().strip() if suffix else ""
        
        text_parts = []
        for sibling in clause.find_next_siblings():
            if "CLAUSE_DEFAULT" in sibling.get("class", []):
                break
            if "ACT_TEXT" in sibling.get("class", []):
                text_parts.append(sibling.get_text().strip())
        
        articles.append(Article(number=number, title=title, text=" ".join(text_parts)))
    
    return articles


def save_articles(articles: list[Article], output_dir: Path, abbrev: str, show_progress=True) -> None:
    """Save articles to txt files and generate metadata.json."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    log_info(f"Сохраняю в {C.CYAN}{output_dir.relative_to(OUTPUT_DIR.parent)}{C.RESET}")
    metadata = []
    
    for i, art in enumerate(articles):
        if show_progress:
            progress_bar(i + 1, len(articles), prefix="Запись   ")
        
        content = f"Статья {art.number} {abbrev}\n{art.title} {art.text}"
        filename = f"{art.number}.txt"
        (output_dir / filename).write_text(content, encoding="utf-8")
        
        metadata.append({
            "law_type": output_dir.name,
            "article_number": art.number,
            "file_path": filename
        })
    
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def is_processed(code_id: str) -> tuple[bool, int]:
    """Check if code was already processed. Returns (is_done, article_count)"""
    folder, *_ = CODES[code_id]
    output_path = OUTPUT_DIR / folder
    metadata_file = output_path / "metadata.json"
    
    if metadata_file.exists():
        try:
            data = json.loads(metadata_file.read_text(encoding="utf-8"))
            return True, len(data)
        except:
            pass
    return False, 0


def parse_code(code_id: str, force=False) -> int:
    """Parse a single code by ID (downloads if needed)."""
    if code_id not in CODES:
        log_error(f"Неизвестный код: {code_id}")
        return 0
    
    folder, abbrev, name, url = CODES[code_id]
    output_dir = OUTPUT_DIR / folder
    
    # Check if already processed
    done, count = is_processed(code_id)
    if done and not force:
        log_info(f"{name} уже обработан ({count} статей)")
        return count
    
    print(f"\n  {C.BOLD}📜 {name}{C.RESET} ({abbrev})")
    print(f"  {C.DIM}{'─' * 50}{C.RESET}")
    
    start = time.time()
    
    try:
        html = download_page(code_id)
    except RuntimeError as e:
        log_error(str(e))
        return 0
    
    articles = extract_articles(html)
    
    if not articles:
        log_error("Статьи не найдены!")
        return 0
    
    save_articles(articles, output_dir, abbrev)
    elapsed = time.time() - start
    
    print(f"  {C.DIM}{'─' * 50}{C.RESET}")
    log_success(f"Готово за {C.BOLD}{elapsed:.1f}с{C.RESET}")
    print(f"""
  {C.GREEN}╭{'─' * 40}╮{C.RESET}
  {C.GREEN}│{C.RESET}  📊 {C.BOLD}Результат:{C.RESET}                          {C.GREEN}│{C.RESET}
  {C.GREEN}│{C.RESET}     Статей: {C.CYAN}{C.BOLD}{len(articles):<26}{C.RESET} {C.GREEN}│{C.RESET}
  {C.GREEN}│{C.RESET}     Папка:  {C.CYAN}{folder:<26}{C.RESET} {C.GREEN}│{C.RESET}
  {C.GREEN}╰{'─' * 40}╯{C.RESET}
""")
    return len(articles)


# ═══════════════════════════════════════════════════════════════════════════════
# Interactive Mode
# ═══════════════════════════════════════════════════════════════════════════════
def show_status():
    """Show all codes with their processing status."""
    print(f"  {C.BOLD}📋 Реестр кодексов:{C.RESET}")
    print(f"  {C.DIM}{'─' * 55}{C.RESET}\n")
    
    processed = 0
    total_articles = 0
    codes_list = list(CODES.items())
    
    for i, (code_id, (folder, abbrev, name, url)) in enumerate(codes_list, 1):
        done, count = is_processed(code_id)
        
        if done:
            status = f"{C.GREEN}✓ {count:>3} ст.{C.RESET}"
            processed += 1
            total_articles += count
        else:
            status = f"{C.DIM}○ ─────{C.RESET}"
        
        # Truncate name if too long
        display_name = name[:28] + ".." if len(name) > 30 else name
        print(f"    {C.CYAN}{i:>2}{C.RESET}. {display_name:<30} {status}")
    
    print(f"\n  {C.DIM}{'─' * 55}{C.RESET}")
    print(f"  {C.BOLD}Обработано:{C.RESET} {C.GREEN}{processed}/{len(CODES)}{C.RESET} кодексов, {C.CYAN}{total_articles}{C.RESET} статей")
    print(f"  {C.BOLD}Вывод в:{C.RESET} {C.DIM}{OUTPUT_DIR}{C.RESET}\n")
    
    return codes_list


def interactive_mode():
    """Interactive menu for processing codes."""
    codes_list = show_status()
    
    print(f"  {C.BOLD}Действия:{C.RESET}")
    print(f"    {C.CYAN}1-{len(codes_list)}{C.RESET}  Обработать конкретный кодекс")
    print(f"    {C.CYAN}a{C.RESET}      Обработать все необработанные")
    print(f"    {C.CYAN}A{C.RESET}      Переобработать ВСЕ (принудительно)")
    print(f"    {C.CYAN}d{C.RESET}      Скачать все страницы в кэш")
    print(f"    {C.CYAN}q{C.RESET}      Выход\n")
    
    try:
        choice = input(f"  {C.BOLD}Выбор:{C.RESET} ").strip()
    except (EOFError, KeyboardInterrupt):
        print(f"\n\n  {C.DIM}До свидания! 👋{C.RESET}\n")
        return
    
    if choice.lower() == 'q':
        print(f"\n  {C.DIM}До свидания! 👋{C.RESET}\n")
        return
    
    elif choice.lower() == 'd':
        # Download all to cache
        print(f"\n  {C.BOLD}Скачивание всех страниц...{C.RESET}\n")
        for code_id in CODES:
            try:
                download_page(code_id)
            except RuntimeError as e:
                log_error(f"{code_id}: {e}")
        log_success("Все страницы в кэше!")
    
    elif choice == 'a':
        # Process all unprocessed
        print()
        total = 0
        for code_id in CODES:
            done, _ = is_processed(code_id)
            if not done:
                total += parse_code(code_id)
        if total:
            print(f"  {C.GREEN}{C.BOLD}═══ ИТОГО: {total} статей ═══{C.RESET}\n")
        else:
            log_info("Все кодексы уже обработаны!")
    
    elif choice == 'A':
        # Force reprocess all
        print()
        total = 0
        for code_id in CODES:
            total += parse_code(code_id, force=True)
        print(f"  {C.GREEN}{C.BOLD}═══ ИТОГО: {total} статей ═══{C.RESET}\n")
    
    elif choice.isdigit() and 1 <= int(choice) <= len(codes_list):
        code_id = codes_list[int(choice) - 1][0]
        parse_code(code_id, force=True)
    
    else:
        log_error("Неверный выбор")


# ═══════════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    banner()
    
    if len(sys.argv) < 2:
        interactive_mode()
    elif sys.argv[1] in ("--all", "-a"):
        # Process all
        total = 0
        for code_id in CODES:
            total += parse_code(code_id)
        print(f"  {C.GREEN}{C.BOLD}═══ ИТОГО: {total} статей ═══{C.RESET}\n")
    elif sys.argv[1] in ("--download", "-d"):
        # Download all
        for code_id in CODES:
            try:
                download_page(code_id)
            except RuntimeError as e:
                log_error(f"{code_id}: {e}")
    elif sys.argv[1] in CODES:
        # Process specific code
        parse_code(sys.argv[1], force="--force" in sys.argv)
    else:
        print(f"  {C.BOLD}Использование:{C.RESET}")
        print(f"    python parser.py              # интерактивный режим")
        print(f"    python parser.py {C.CYAN}<code_id>{C.RESET}     # обработать один кодекс")
        print(f"    python parser.py {C.CYAN}--all{C.RESET}        # обработать все")
        print(f"    python parser.py {C.CYAN}--download{C.RESET}   # скачать все в кэш\n")
        print(f"  {C.BOLD}Доступные коды:{C.RESET}")
        for cid, (_, _, name, _) in CODES.items():
            print(f"    {C.CYAN}{cid}{C.RESET} → {name}")
