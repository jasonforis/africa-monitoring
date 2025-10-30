#!/usr/bin/env python3
"""
Мониторинг Африки - генерация обзоров по африканским странам
"""

import asyncio
import httpx
import json
import math
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API endpoints
API_URL = "https://beta.index.ru/mf-api/"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

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


async def generate_country_overview(country_name: str, headlines: List[Dict], mentions: int) -> Dict:
    """
    Генерирует AI-обзор для страны
    
    Args:
        country_name: Название страны
        headlines: Список новостей
        mentions: Количество упоминаний
    
    Returns:
        Dict с полями:
            - title: Заголовок обзора
            - summary: Краткая сводка
            - full_text: Полный текст обзора
    """
    try:
        if not headlines or len(headlines) == 0:
            return {
                "title": f"{country_name}: Нет новостей",
                "summary": "Информация обновляется...",
                "full_text": "Информация обновляется..."
            }
        
        # Берём первые 3 новости для анализа
        news_texts = []
        for news in headlines[:3]:
            source = news.get('source', '')
            time = news.get('time', '')
            snippet = news.get('msg', '')
            news_texts.append(f"[{source}, {time}] {snippet[:500]}")
        
        news_context = "\n\n".join(news_texts)
        
        prompt = f"""Ты - новостной аналитик. На основе новостей напиши обзор по стране {country_name}.

Новости:
{news_context}

Требования:
1. Создай короткий заголовок (5-7 слов) - главное событие в стране
2. Напиши краткую сводку (2-3 предложения) - что происходит
3. Напиши полный обзор (3-4 абзаца):
   - Что происходит (главное событие)
   - Контекст и детали
   - Значение для региона/мира

Стиль:
- КОНКРЕТНЫЕ факты: кто, что, где, когда
- Избегай общих фраз
- Пиши информативно и лаконично

Формат ответа (строго JSON):
{{
  "title": "Заголовок обзора",
  "summary": "Краткая сводка в 2-3 предложения.",
  "full_text": "Полный обзор в 3-4 абзаца."
}}

Ответ (только JSON):"""

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "google/gemini-2.0-flash-exp:free",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.7
                }
            )
            
            if response.status_code != 200:
                logger.error(f"OpenRouter вернул статус {response.status_code}")
                return {
                    "title": f"{country_name}: Информация обновляется",
                    "summary": "Информация обновляется...",
                    "full_text": "Информация обновляется..."
                }
            
            result = response.json()
            ai_response = result["choices"][0]["message"]["content"].strip()
            
            # Извлекаем JSON из ответа
            if "```json" in ai_response:
                ai_response = ai_response.split("```json")[1].split("```")[0].strip()
            elif "```" in ai_response:
                ai_response = ai_response.split("```")[1].split("```")[0].strip()
            
            overview = json.loads(ai_response)
            return overview
                
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
    
    # Шаг 2: Генерируем обзоры для каждой страны
    countries_with_overviews = []
    
    for i, country in enumerate(countries_data, 1):
        country_name = country.get("category_name", "")
        mentions = country.get("mentions_count", 0)
        growth = country.get("growth_percentage", 0)
        headlines = country.get("headlines", [])
        image_url = country.get("category_image_url", "")
        
        # Конвертируем mentions в int
        mentions = int(mentions) if mentions else 0
        
        logger.info(f"[{i}/{len(countries_data)}] Генерация обзора для: {country_name} ({mentions} упоминаний)")
        
        overview = await generate_country_overview(country_name, headlines, mentions)
        
        countries_with_overviews.append({
            "country_name": country_name,
            "mentions_count": mentions,
            "growth_percentage": growth,
            "image_url": image_url,
            "title": overview["title"],
            "summary": overview["summary"],
            "full_text": overview["full_text"],
            "headlines": headlines
        })
    
    # Сортируем по количеству упоминаний
    countries_with_overviews.sort(key=lambda x: x["mentions_count"], reverse=True)
    
    # Шаг 3: Сохраняем результат
    output_data = {
        "generated_at": datetime.now().isoformat(),
        "total_countries": len(countries_with_overviews),
        "countries": countries_with_overviews
    }
    
    output_file = os.path.join(OUTPUT_DIR, "africa_monitoring.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✓ Сохранено в {output_file}")
    logger.info(f"  Всего стран: {len(countries_with_overviews)}")
    logger.info(f"  Топ-3:")
    for i, country in enumerate(countries_with_overviews[:3], 1):
        logger.info(f"    {i}. {country['country_name']}: {country['mentions_count']} упоминаний")
    
    logger.info("=" * 60)
    logger.info("МОНИТОРИНГ АФРИКИ ЗАВЕРШЁН")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(generate_africa_monitoring())

