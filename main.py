import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import warnings
import time
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

warnings.filterwarnings("ignore", category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Парсер uub.in.ua", layout="wide")

st.title("Парсер лотів з uub.in.ua (Земля)")

st.markdown("""
Встав посилання на будь-яку сторінку з лотами (з фільтрами чи без).  
Парсер автоматично додасть/змінить параметр `page=N` для всіх наступних сторінок.  
Поки сайт видає 503 — нічого не працюватиме. Перевір статус: https://downforeveryoneorjustme.com/uub.in.ua
""")

# Поля вводу
col1, col2 = st.columns([3, 1])

with col1:
    url_input = st.text_input(
        "Посилання на сторінку з лотами",
        value="https://uub.in.ua/collection/zemlya",
        help="Наприклад: https://uub.in.ua/collection/zemlya?page=1 або з будь-якими фільтрами"
    )

with col2:
    max_pages = st.number_input(
        "Максимальна кількість сторінок",
        min_value=1,
        max_value=200,
        value=5,
        step=1,
        help="Не став більше 50–100 одразу — можуть заблокувати IP за швидкі запити"
    )

delay_seconds = st.slider(
    "Пауза між запитами (сек)",
    min_value=1.0,
    max_value=10.0,
    value=2.5,
    step=0.5,
    help="Більша пауза — менший ризик бану"
)

if st.button("Почати парсинг", type="primary"):
    if not url_input.strip():
        st.error("Вкажіть посилання!")
        st.stop()

    with st.spinner(f"Парсинг {max_pages} сторінок..."):
        all_lots = []
        current_base_url = url_input.strip()

        # Очищаємо існуючий параметр page
        parsed = urlparse(current_base_url)
        query_params = parse_qs(parsed.query)
        query_params.pop('page', None)  # видаляємо page якщо був
        cleaned_query = urlencode(query_params, doseq=True)

        base_url_no_page = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            cleaned_query,
            parsed.fragment
        ))

        if base_url_no_page.endswith('?'):
            base_url_no_page = base_url_no_page[:-1]

        page = 1
        while page <= max_pages:
            st.write(f"Обробка сторінки {page} з {max_pages}...")

            # Формуємо URL
            if '?' in base_url_no_page:
                page_url = f"{base_url_no_page}&page={page}"
            else:
                page_url = f"{base_url_no_page}?page={page}"

            try:
                resp = requests.get(
                    page_url,
                    timeout=30,
                    verify=False,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                st.error(f"Помилка на сторінці {page}: {str(e)}")
                if "503" in str(e) or "Service Unavailable" in str(e):
                    st.info("Сайт видає 503 Service Unavailable — зачекай 1–24 години.")
                elif "SSLError" in str(e):
                    st.info("Проблема з SSL-сертифікатом сайту. verify=False вже включено.")
                break

            soup = BeautifulSoup(resp.text, 'html.parser')

            # Універсальний пошук можливих карток лотів
            candidates = soup.find_all(['div', 'article', 'section', 'li'], class_=lambda c: c and any(
                word in c.lower() for word in ['lot', 'auction', 'card', 'item', 'col-', 'mb-', 'shadow', 'product']
            ))

            found_on_page = 0

            for card in candidates:
                lot = {}

                # Опис / основний текст
                desc_candidates = card.find_all(['h1','h2','h3','h4','h5','p','div','span'])
                desc = ""
                for tag in desc_candidates:
                    txt = tag.get_text(strip=True)
                    if len(txt) > 20 and any(kw in txt.lower() for kw in ['ділянка','га','кадастров','площе','номер']):
                        desc = txt
                        break
                lot['Опис'] = desc or card.get_text(strip=True)[:250] + '...' or 'N/A'

                # Ціна
                price_texts = card.find_all(string=lambda t: t and any(c in t for c in ['UAH','грн','₴','.',',']) and any(d in t for d in '0123456789'))
                lot['Ціна'] = price_texts[0].strip() if price_texts else 'N/A'

                # Номер лоту
                lot_num = card.find(string=lambda t: t and ('лот' in t.lower() or t.strip().isdigit() and 5 <= len(t.strip()) <= 8))
                lot['Номер лоту'] = lot_num.strip() if lot_num else 'N/A'

                # Область
                oblast = card.find(string=lambda t: t and 'обл.' in t)
                lot['Область'] = oblast.strip() if oblast else 'N/A'

                # Дата
                date_str = card.find(string=lambda t: t and ('Дата' in t or '-' in t and len(t.split('-')) >= 2))
                lot['Дата'] = date_str.strip() if date_str else 'N/A'

                # Посилання
                a = card.find('a', href=True)
                lot['Посилання'] = ('https://uub.in.ua' + a['href'] if a else 'N/A') if a else 'N/A'

                # Фото
                img = card.find('img', src=True)
                lot['Фото'] = img['src'] if img else 'N/A'

                if lot['Опис'] != 'N/A' or lot['Ціна'] != 'N/A' or lot['Номер лоту'] != 'N/A':
                    all_lots.append(lot)
                    found_on_page += 1

            st.write(f"Знайдено на сторінці {page}: {found_on_page} потенційних лотів")

            if found_on_page == 0:
                st.info(f"Сторінка {page} здається порожньою або кінець списку.")
                break

            time.sleep(delay_seconds)  # пауза між запитами
            page += 1

        # Результат
        if all_lots:
            df = pd.DataFrame(all_lots)
            st.success(f"Зібрано {len(all_lots)} записів з {page-1} сторінок")

            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="Скачати як CSV",
                data=csv,
                file_name=f"uub_lots_{len(all_lots)}_записів.csv",
                mime="text/csv"
            )
        else:
            st.warning("Не вдалося знайти жодного лоту. Можливі причини:")
            st.markdown("""
            - Сайт досі видає 503 або недоступний
            - Сторінки завантажуються через JavaScript (потрібен Selenium)
            - Потрібні точніші селектори (пришли outerHTML однієї картки лоту з F12)
            """)

st.markdown("---")
st.caption("Парсер створено для особистого використання. Не використовуй для масового скрейпінгу без дозволу сайту.")
