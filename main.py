import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import warnings
import time
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Парсер uub.in.ua — усі кандидати", layout="wide")

st.title("Парсер лотів з uub.in.ua — максимальне захоплення кандидатів")

st.markdown("""
Парсер намагається витягнути **всі можливі картки лотів** на сторінці,  
навіть якщо вони не містять усіх ключових слів.  
Це може включати трохи сміття, але ви отримаєте значно більше даних.
""")

col1, col2, col3 = st.columns([4, 1, 1])

with col1:
    url_input = st.text_input(
        "Посилання на сторінку з лотами",
        value="https://uub.in.ua/collection/zemlya",
        help="Може бути з фільтрами або без"
    )

with col2:
    max_pages = st.number_input("Макс. сторінок", min_value=1, max_value=200, value=10, step=1)

with col3:
    delay_sec = st.slider("Пауза між запитами (сек)", 1.0, 8.0, 3.0, 0.5)

if st.button("Парсити всіх кандидатів", type="primary"):
    if not url_input.strip():
        st.error("Вкажіть посилання!")
        st.stop()

    with st.spinner(f"Парсинг до {max_pages} сторінок..."):
        all_lots = []
        seen_links = set()  # уникнення дублів за посиланням

        # Очищення базового URL від page
        parsed = urlparse(url_input.strip())
        q = parse_qs(parsed.query)
        q.pop('page', None)
        base_query = urlencode(q, doseq=True)
        base_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, base_query, parsed.fragment))
        if base_url.endswith('?'):
            base_url = base_url[:-1]

        page = 1
        while page <= max_pages:
            st.write(f"Сторінка {page} з {max_pages}...")

            page_url = f"{base_url}&page={page}" if '?' in base_url else f"{base_url}?page={page}"

            try:
                r = requests.get(
                    page_url,
                    timeout=30,
                    verify=False,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                r.raise_for_status()
            except Exception as e:
                st.error(f"Сторінка {page} — помилка: {str(e)}")
                break

            soup = BeautifulSoup(r.text, 'html.parser')

            # Дуже широкий пошук кандидатів — майже всі блоки, які можуть бути картками
            candidates_tags = ['div', 'article', 'section', 'li', 'figure', 'a']
            candidates_classes = [
                'lot', 'auction', 'card', 'item', 'product', 'tile', 'block', 'entry', 'post',
                'col-', 'mb-', 'shadow', 'grid-item', 'list-item', 'thumbnail', 'media', 'panel'
            ]

            candidates = []
            for tag in candidates_tags:
                for cls in candidates_classes:
                    candidates.extend(soup.find_all(tag, class_=lambda x: x and cls in x.lower()))

            # Якщо мало — беремо всі div з href всередині або з img
            if len(candidates) < 10:
                candidates = soup.find_all(['div', 'li'], recursive=False)
                candidates = [c for c in candidates if c.find('a') or c.find('img')]

            found_on_page = 0

            for card in candidates:
                # Витягуємо весь чистий текст
                text = card.get_text(separator=' ', strip=True).replace('\n', ' ').replace('  ', ' ')
                if len(text) < 40:
                    continue  # надто короткий блок — пропускаємо

                lot = {'Повний текст': text[:600] + '...' if len(text) > 600 else text}

                # Посилання (найважливіше для унікальності)
                a = card.find('a', href=True)
                link = None
                if a:
                    href = a['href']
                    link = 'https://uub.in.ua' + href if href.startswith('/') else href
                lot['Посилання'] = link or 'N/A'

                if link in seen_links:
                    continue  # дубль
                seen_links.add(link)

                # Фото
                img = card.find('img', src=True)
                lot['Фото'] = img['src'] if img else 'N/A'

                # Ціна (будь-яке число з грн/UAH)
                price_m = re.search(r'(\d{1,3}(?:\s*\d{3})*(?:[.,]\d{1,2})?)\s*(UAH|грн|₴|гривень)', text, re.I)
                lot['Ціна'] = price_m.group(0) if price_m else 'N/A'

                # Номер лоту
                lot_num_m = re.search(r'(?:лот|№|номер лоту|Лот №?)\s*[:\-]?\s*(\d{5,8})', text, re.I)
                lot['Номер лоту'] = lot_num_m.group(1) if lot_num_m else 'N/A'

                # Область
                oblast_m = re.search(r'(?:Область|обл\.|регіон)\s*[:\-]?\s*([^,\.\n]+?)(?:\s+обл|\s*$)', text, re.I)
                lot['Область'] = oblast_m.group(1).strip() if oblast_m else 'N/A'

                # Площа / га
                area_m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:га|гектар|га\.)', text, re.I)
                lot['Площа (га)'] = area_m.group(0) if area_m else 'N/A'

                # Кадастровий номер
                kadas_m = re.search(r'(?:\d{10,15}(?::\d{1,5}){3,5})|(?:кадастр|КН)\s*[:\-]?\s*(\d{10,15}(?::\d{1,5}){3,5})', text, re.I)
                lot['Кадастровий номер'] = kadas_m.group(1) if kadas_m else 'N/A'

                # Дата
                date_m = re.search(r'(?:Дата|початку|аукціону)\s*[:\-]?\s*([\d\.\-]{8,20})', text, re.I)
                lot['Дата'] = date_m.group(1).strip() if date_m else 'N/A'

                all_lots.append(lot)
                found_on_page += 1

            st.write(f"Сторінка {page}: знайдено кандидатів — **{found_on_page}**")

            if found_on_page < 5:
                st.info(f"Мало кандидатів на сторінці {page}. Можливо, кінець списку або сайт змінив структуру.")
                break

            time.sleep(delay_sec)
            page += 1

        # Підсумок
        if all_lots:
            df = pd.DataFrame(all_lots)
            st.success(f"Зібрано **{len(all_lots)}** потенційних лотів з {page-1} сторінок")

            st.dataframe(df, use_container_width=True, column_config={
                "Повний текст": st.column_config.TextColumn(width="medium"),
                "Посилання": st.column_config.LinkColumn()
            })

            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "Скачати CSV (всі кандидати)",
                csv,
                f"uub_candidates_{len(all_lots)}.csv",
                "text/csv"
            )
        else:
            st.warning("Не знайдено жодного кандидата. Сайт може бути недоступним або контент завантажується через JS.")
