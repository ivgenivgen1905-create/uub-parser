import requests
from bs4 import BeautifulSoup
import pandas as pd

# Базовий URL з твоїм фільтром
BASE_URL = "https://uub.in.ua/collection/zemlya"
PARAMS = {
    "Auctions[region]": "Харківська обл.",
    "Auctions[lot_price_from]": "",
    "Auctions[lot_price_to]": "",
    "Auctions[from_date]": "",
    "Auctions[to_date]": "",
    "Auctions[state]": "",
    "Auctions[lot_number]": "",
    "Auctions[encumbrance_of_property]": ""
}

def parse_uub_page(url, params):
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Помилка якщо не 200
    except requests.exceptions.HTTPError as e:
        print(f"Помилка запиту: {e} (можливо, сайт недоступний, статус {response.status_code})")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    
    lots = []
    # Знаходимо картки лотів (на основі структури сайту: div з class 'lot-item' або подібне — адаптуй якщо зміниться)
    lot_items = soup.find_all('div', class_='lot-item')  # Змініть class на актуальний (перевірте HTML)
    
    for item in lot_items:
        lot = {}
        
        # Лот номер
        lot['lot_number'] = item.find('span', class_='lot-number').text.strip() if item.find('span', class_='lot-number') else 'N/A'
        
        # Опис/назва
        lot['description'] = item.find('h3', class_='lot-title').text.strip() if item.find('h3', class_='lot-title') else 'N/A'
        
        # Стартова ціна
        lot['start_price'] = item.find('span', class_='start-price').text.strip() if item.find('span', class_='start-price') else 'N/A'
        
        # Дата аукціону
        lot['auction_date'] = item.find('span', class_='auction-date').text.strip() if item.find('span', class_='auction-date') else 'N/A'
        
        # Статус
        lot['status'] = item.find('span', class_='status').text.strip() if item.find('span', class_='status') else 'N/A'
        
        # Регіон (вже фільтр, але витягуємо якщо є)
        lot['region'] = item.find('span', class_='region').text.strip() if item.find('span', class_='region') else 'Харківська обл.'
        
        # Площа (area), кадастровий номер тощо — шукаємо в деталях
        details = item.find('div', class_='lot-details')
        if details:
            lot['area'] = details.find('span', class_='area').text.strip() if details.find('span', class_='area') else 'N/A'
            lot['cadastral'] = details.find('span', class_='cadastral').text.strip() if details.find('span', class_='cadastral') else 'N/A'
            lot['encumbrance'] = details.find('span', class_='encumbrance').text.strip() if details.find('span', class_='encumbrance') else 'N/A'
        
        # Посилання на лот
        lot['link'] = 'https://uub.in.ua' + item.find('a', class_='lot-link')['href'] if item.find('a', class_='lot-link') else 'N/A'
        
        lots.append(lot)
    
    return lots

# Функція для пагінації (якщо потрібно всі сторінки)
def parse_all_pages(base_url, params, max_pages=5):  # Обмежуємо, щоб не забанили
    all_lots = []
    page = 1
    while page <= max_pages:
        params['page'] = page
        lots = parse_uub_page(base_url, params)
        if not lots:
            break
        all_lots.extend(lots)
        page += 1
        # Перевірка на наступну сторінку (адаптувати за HTML)
        # Якщо немає більше — break
    return all_lots

# Запуск
lots_data = parse_all_pages(BASE_URL, PARAMS)

if lots_data:
    # Дублюємо дані: спочатку як список
    print("Сирі дані (дубльовані як список диктів):")
    for lot in lots_data:
        print(lot)
    
    # Потім як таблиця (pandas)
    df = pd.DataFrame(lots_data)
    print("\nТаблиця з даними:")
    print(df.to_string(index=False))  # Або df.to_csv('uub_lots.csv') для файлу
else:
    print("Немає даних — перевір сайт або параметри.")
