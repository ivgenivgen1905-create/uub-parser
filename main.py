import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import warnings

warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

st.title("Парсер лотів з uub.in.ua")

st.info("Встав посилання на сторінку з лотами (наприклад, https://uub.in.ua/collection/zemlya?... з твоїми фільтрами). Якщо сайт видає 503 або SSL-помилку — почекай, це тимчасово.")

url_input = st.text_input(
    "Встав посилання на сторінку аукціонів",
    value="https://uub.in.ua/collection/zemlya?Auctions%5Bregion%5D=%D0%A5%D0%B0%D1%80%D0%BA%D1%96%D0%B2%D1%81%D1%8C%D0%BA%D0%B0+%D0%BE%D0%B1%D0%BB.&Auctions%5Blot_price_from%5D=&Auctions%5Blot_price_to%5D=&Auctions%5Bfrom_date%5D=&Auctions%5Bto_date%5D=&Auctions%5Bstate%5D=&Auctions%5Blot_number%5D=&Auctions%5Bencumbrance_of_property%5D=",
    help="Можеш змінити фільтри в URL і вставити нове посилання"
)

max_pages = st.number_input("Максимальна кількість сторінок для парсингу", min_value=1, max_value=20, value=3)

if st.button("Парсити сторінку(і)"):
    if not url_input:
        st.error("Встав посилання!")
    else:
        with st.spinner("Парсимо... (може зайняти 10–60 секунд залежно від кількості сторінок)"):
            all_lots = []

            current_url = url_input
            for page in range(1, max_pages + 1):
                try:
                    st.write(f"Обробляємо сторінку {page}...")
                    response = requests.get(current_url, timeout=15, verify=False)
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    st.error(f"Помилка доступу до сайту на сторінці {page}: {str(e)}")
                    st.info("Ймовірно, сайт тимчасово недоступний (503 або SSL-проблема). Спробуй пізніше або перевір у браузері.")
                    break

                soup = BeautifulSoup(response.text, 'html.parser')

                # Адаптуй ці селектори під реальну структуру сайту!
                # Відкрий сторінку в браузері → F12 → подивись класи/теги лотів
                lot_items = soup.find_all('div', class_='lot-item')  # ← ЗМІНИ НА АКТУАЛЬНИЙ КЛАС!

                if not lot_items:
                    st.warning(f"На сторінці {page} не знайдено лотів. Можливо, кінець списку або неправильні селектори.")
                    break

                for item in lot_items:
                    lot = {}

                    # Приклади — заміни на реальні класи/теги
                    lot['lot_number'] = item.find('span', class_='lot-number') or item.find('div', class_='lot-num') or 'N/A'
                    if lot['lot_number'] != 'N/A':
                        lot['lot_number'] = lot['lot_number'].get_text(strip=True)

                    lot['description'] = item.find('h3') or item.find('a', class_='lot-title') or 'N/A'
                    if lot['description'] != 'N/A':
                        lot['description'] = lot['description'].get_text(strip=True)

                    lot['start_price'] = item.find(string=lambda t: 'грн' in t) or 'N/A'  # простий пошук по тексту
                    lot['auction_date'] = item.find(string=lambda t: 'Дата' in t or '.' in t and len(t.split('.'))==3) or 'N/A'

                    # Додай інші поля: площа, кадастр, обтяження тощо
                    # Приклад:
                    # lot['area'] = item.find('span', class_='area-m2').get_text(strip=True) if ... else 'N/A'

                    lot['link'] = item.find('a')['href'] if item.find('a') else 'N/A'
                    if lot['link'] != 'N/A' and not lot['link'].startswith('http'):
                        lot['link'] = 'https://uub.in.ua' + lot['link']

                    all_lots.append(lot)

                # Пагінація: знайди посилання на наступну сторінку
                next_link = soup.find('a', text='Наступна') or soup.find('a', {'rel': 'next'})
                if next_link and 'href' in next_link.attrs:
                    current_url = 'https://uub.in.ua' + next_link['href']
                else:
                    st.info("Досягнуто кінець сторінок або пагінація не знайдена.")
                    break

            if all_lots:
                df = pd.DataFrame(all_lots)
                st.success(f"Знайдено {len(all_lots)} лотів!")

                st.dataframe(df)  # показуємо таблицю в апці

                # Скачування
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="Скачати таблицю як CSV",
                    data=csv,
                    file_name="uub_lots.csv",
                    mime="text/csv"
                )
            else:
                st.warning("Не вдалося знайти жодного лоту. Перевір селектори в коді або посилання.")
