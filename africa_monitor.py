#!/usr/bin/env python3
"""
Мониторинг Африки - генерация обзоров по африканским странам
"""

import asyncio
import httpx
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import quote

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API endpoints
API_URL = "https://beta.index.ru/mf-api/"

# Выходная директория
OUTPUT_DIR = "/tmp/africa_data"


async def fetch_page_with_retry(client: httpx.AsyncClient, page_num: int = None, max_retries: int = 3) -> Optional[List[Dict]]:
    """
    Получает одну страницу с повторными попытками
    """
    params = {"page": "main", "gid": "104"}
    if page_num is not None:
        params["n"] = page_num
    
    for attempt in range(max_retries):
        try:
            response = await client.get(API_URL, params=params, timeout=30.0)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return data
            
            logger.warning(f"Попытка {attempt + 1}/{max_retries}: статус {response.status_code}")
            
        except Exception as e:
            logger.warning(f"Попытка {attempt + 1}/{max_retries}: {str(e)[:100]}")
            
        # Ждём перед следующей попыткой
        if attempt < max_retries - 1:
            await asyncio.sleep(2)
    
    return None


async def fetch_country_news(client: httpx.AsyncClient, country_name: str, max_retries: int = 3) -> List[Dict]:
    """
    Получает новости по стране через поисковый API
    
    Args:
        client: HTTP клиент
        country_name: Название страны
        max_retries: Количество повторных попыток
    
    Returns:
        Список новостей
    """
    params = {"q": country_name}
    
    for attempt in range(max_retries):
        try:
            response = await client.get(API_URL, params=params, timeout=30.0)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Возвращаем headlines из первого результата
                    headlines = data[0].get("headlines", [])
                    logger.info(f"  ✓ Получено {len(headlines)} новостей по {country_name}")
                    return headlines
            
            logger.warning(f"  Попытка {attempt + 1}/{max_retries}: статус {response.status_code}")
            
        except Exception as e:
            logger.warning(f"  Попытка {attempt + 1}/{max_retries}: {str(e)[:100]}")
            
        # Ждём перед следующей попыткой
        if attempt < max_retries - 1:
            await asyncio.sleep(2)
    
    return []


async def fetch_all_african_countries() -> List[Dict]:
    """
    Получает все африканские страны через пагинацию API
    
    Returns:
        Список всех стран с данными
    """
    all_countries = []
    
    try:
        async with httpx.AsyncClient() as client:
            # Первая страница без параметра n
            logger.info(f"[API] Запрос первой страницы (без n)")
            data = await fetch_page_with_retry(client, page_num=None)
            if data:
                all_countries.extend(data)
                logger.info(f"[API] ✓ Получено {len(data)} стран с первой страницы")
            else:
                logger.warning(f"[API] ✗ Не удалось получить первую страницу")
            
            # Страницы 2-10
            for page_num in range(2, 11):
                logger.info(f"[API] Запрос страницы {page_num}")
                data = await fetch_page_with_retry(client, page_num=page_num)
                
                if not data:
                    logger.info(f"[API] Страница {page_num} недоступна, останавливаем пагинацию")
                    break
                
                if len(data) == 0:
                    logger.info(f"[API] Страница {page_num} пустая, останавливаем пагинацию")
                    break
                
                all_countries.extend(data)
                logger.info(f"[API] ✓ Получено {len(data)} стран со страницы {page_num}")
                
                # Если получили меньше 10, значит это последняя страница
                if len(data) < 10:
                    logger.info(f"[API] Последняя страница (получено < 10 стран)")
                    break
            
            logger.info(f"[API] ✓ Всего получено {len(all_countries)} африканских стран")
            return all_countries
                
    except Exception as e:
        logger.error(f"Критическая ошибка при получении африканских стран: {e}")
        return all_countries if all_countries else []


def generate_country_overview_from_news(country_name: str, headlines: List[Dict]) -> Dict:
    """
    Генерирует обзор для страны на основе новостей из API
    
    Args:
        country_name: Название страны
        headlines: Список новостей из API
    
    Returns:
        Dict с полями:
            - title: Заголовок обзора (первая новость)
            - summary: Краткая сводка (первые 3 новости)
            - full_text: Полный текст (все новости)
    """
    try:
        if not headlines or len(headlines) == 0:
            return {
                "title": f"{country_name}: Нет новостей",
                "summary": "Информация обновляется...",
                "full_text": "Информация обновляется..."
            }
        
        # Заголовок - первая новость
        first_news = headlines[0]
        title = first_news.get('msg', f"{country_name}: Нет заголовка")[:100]
        
        # Краткая сводка - первые 3 новости
        summary_parts = []
        for news in headlines[:3]:
            msg = news.get('msg', '')
            if msg:
                summary_parts.append(msg[:200])
        summary = " • ".join(summary_parts) if summary_parts else "Информация обновляется..."
        
        # Полный текст - все новости
        full_text_parts = []
        for i, news in enumerate(headlines[:10], 1):  # Берём первые 10 новостей
            source = news.get('source', 'Источник неизвестен')
            time = news.get('time', '')
            msg = news.get('msg', '')
            
            if msg:
                full_text_parts.append(f"{i}. [{source}] {msg}")
        
        full_text = "\n\n".join(full_text_parts) if full_text_parts else "Информация обновляется..."
        
        return {
            "title": title,
            "summary": summary,
            "full_text": full_text
        }
                
    except Exception as e:
        logger.error(f"Ошибка при генерации обзора для {country_name}: {e}")
        return {
            "title": f"{country_name}: Информация обновляется",
            "summary": "Информация обновляется...",
            "full_text": "Информация обновляется..."
        }


async def generate_africa_monitoring():
    """
    Генерирует полный мониторинг Африки
    """
    logger.info("=" * 60)
    logger.info("ГЕНЕРАЦИЯ МОНИТОРИНГА АФРИКИ")
    logger.info("=" * 60)
    
    # Создаём выходную директорию
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Шаг 1: Получаем все африканские страны
    countries_data = await fetch_all_african_countries()
    
    if not countries_data:
        logger.error("Не удалось получить данные по африканским странам")
        return
    
    logger.info(f"Получено {len(countries_data)} стран")
    
    # Шаг 2: Получаем новости и генерируем обзоры для каждой страны
    countries_with_overviews = []
    
    async with httpx.AsyncClient() as client:
        for i, country in enumerate(countries_data, 1):
            country_name = country.get("category_name", "")
            mentions = country.get("mentions_count", 0)
            growth = country.get("growth_percentage", 0)
            image_url = country.get("category_image_url", "")
            
            # Конвертируем mentions в int
            mentions = int(mentions) if mentions else 0
            
            logger.info(f"[{i}/{len(countries_data)}] Обработка: {country_name} ({mentions} упоминаний)")
            
            # Получаем новости по стране через поисковый API
            headlines = await fetch_country_news(client, country_name)
            
            # Генерируем обзор на основе новостей
            overview = generate_country_overview_from_news(country_name, headlines)
            
            countries_with_overviews.append({
                "country_name": country_name,
                "mentions_count": mentions,
                "growth_percentage": growth,
                "image_url": image_url,
                "title": overview["title"],
                "summary": overview["summary"],
                "full_text": overview["full_text"],
                "headlines": headlines[:10]  # Сохраняем первые 10 новостей
            })
    
    # Сортируем по количеству упоминаний
    countries_with_overviews.sort(key=lambda x: x["mentions_count"], reverse=True)
    
    # Шаг 3: Сохраняем результат
    output_data = {
        "generated_at": datetime.now().isoformat(),
        "total_countries": len(countries_with_overviews),
        "total_mentions": sum(c["mentions_count"] for c in countries_with_overviews),
        "countries": countries_with_overviews
    }
    
    output_file = os.path.join(OUTPUT_DIR, "africa_monitoring.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✓ Сохранено в {output_file}")
    logger.info(f"  Всего стран: {len(countries_with_overviews)}")
    logger.info(f"  Всего упоминаний: {output_data['total_mentions']}")
    logger.info(f"  Топ-3:")
    for i, country in enumerate(countries_with_overviews[:3], 1):
        logger.info(f"    {i}. {country['country_name']}: {country['mentions_count']} упоминаний")
    
    logger.info("=" * 60)
    logger.info("МОНИТОРИНГ АФРИКИ ЗАВЕРШЁН")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(generate_africa_monitoring())

