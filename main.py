import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import warnings

warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

st.title("Парсер лотів з uub.in.ua")

url_input = st.text_input(
    "Встав посилання на сторінку з лотами",
    value="https://uub.in.ua/collection/zemlya"
)

max_pages = st.number_input("Макс. сторінок", min_value=1, max_value=10, value=1)

if st.button("Парсити"):
    if not url_input:
        st.error("Встав посилання!")
    else:
        with st.spinner("Парсинг..."):
            all_lots = []
            current_url = url_input
            page = 1

            while page <= max_pages:
                st.write(f"Сторінка {page}...")
                try:
                    resp = requests.get(current_url, timeout=20, verify=False)
                    resp.raise_for_status()
                except Exception as e:
                    st.error(f"Помилка на сторінці {page}: {str(e)} (сайт може бути недоступний)")
                    break

                soup = BeautifulSoup(resp.text, 'html.parser')

                # Знаходимо можливі контейнери лотів
                lot_containers = (
                    soup.find_all('div', class_=['card', 'auction-card', 'lot-card', 'col-md-4', 'col-lg-3', 'mb-4']) or
                    soup.find_all('div', recursive=False)  # fallback
                )

                found = False
                for container in lot_containers:
                    lot = {}

                    # Опис (перший великий текст)
                    desc_tag = container.find(['h5', 'h4', 'h3', 'div'], string=lambda t: t and ('ділянка' in t.lower() or 'земель' in t.lower() or 'площею' in t.lower()))
                    lot['description'] = desc_tag.get_text(strip=True) if desc_tag else container.get_text(strip=True)[:200] + '...' if container.get_text(strip=True) else 'N/A'

                    # Ціна (шукаємо по "Стартова ціна" або числу з крапкою)
                    price_tag = container.find(string=lambda t: t and ('UAH' in t or '.' in t and t.replace('.', '').isdigit()))
                    lot['start_price'] = price_tag.strip() if price_tag else 'N/A'

                    # Область / регіон
                    region_tag = container.find(string=lambda t: t and 'обл.' in t)
                    lot['oblast'] = region_tag.strip() if region_tag else 'N/A'

                    # Номер лоту
                    lot_num_tag = container.find(string=lambda t: t and ('Номер лоту' in t or t.strip().isdigit() and len(t.strip()) > 5))
                    lot['lot_number'] = lot_num_tag.strip() if lot_num_tag else 'N/A'

                    # Дата початку
                    date_tag = container.find(string=lambda t: t and ('Дата' in t or '-' in t and len(t.split('-')) == 3))
                    lot['start_date'] = date_tag.strip() if date_tag else 'N/A'

                    # Посилання
                    a_tag = container.find('a', href=True)
                    lot['link'] = 'https://uub.in.ua' + a_tag['href'] if a_tag else 'N/A'

                    # Фото (перше img)
                    img = container.find('img')
                    lot['image'] = img['src'] if img and 'src' in img.attrs else 'N/A'

                    if lot['description'] != 'N/A' or lot['start_price'] != 'N/A':
                        all_lots.append(lot)
                        found = True

                if not found:
                    st.warning(f"На сторінці {page} не знайдено лотів за поточними селекторами. Сайт може використовувати JS-завантаження або іншу структуру.")
                    break

                # Пагінація (шукаємо "Наступна")
                next_a = soup.find('a', string=lambda t: t and ('Наступна' in t or '>' in t))
                if next_a and 'href' in next_a.attrs:
                    current_url = 'https://uub.in.ua' + next_a['href']
                else:
                    break

                page += 1

            if all_lots:
                df = pd.DataFrame(all_lots)
                st.success(f"Знайдено {len(all_lots)} лотів")
                st.dataframe(df)

                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("Скачати CSV", csv, "uub_lots.csv", "text/csv")
            else:
                st.error("Лоти не знайдено. Можливо:")
                st.markdown("""
                - Сайт тимчасово недоступний (503)
                - Сторінка завантажується JavaScript'ом (потрібен Selenium/Playwright)
                - Потрібно точніше налаштувати селектори
                """)
