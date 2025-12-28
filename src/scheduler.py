import json
import os
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from crawl4ai import AsyncWebCrawler
from src import database

def load_sources():
    try:
        with open("sources.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Scheduler] Error loading sources.json: {e}")
        return []

async def crawl_and_index():
    """
    Scrapes URLs from sources.json and indexes them into ChromaDB.
    """
    urls = load_sources()
    if not urls:
        print("[Scheduler] No sources to scrape.")
        return

    print(f"[Scheduler] Starting scrape job for {len(urls)} sources...")
    
    async with AsyncWebCrawler(verbose=True) as crawler:
        for url in urls:
            try:
                print(f"[Scheduler] Scraping: {url}")
                result = await crawler.arun(url=url)
                
                if result.success:
                    # Store in database
                    # We use the URL as the filename/id
                    content = f"Source: {url}\n\n{result.markdown}"
                    database.vectorize_file(file_path=url, content=content)
                    print(f"[Scheduler] Indexed: {url}")
                else:
                    print(f"[Scheduler] Failed to scrape {url}: {result.error_message}")
                    
            except Exception as e:
                print(f"[Scheduler] Error processing {url}: {e}")

def run_scraper_job():
    """
    Wrapper to run the async scraper in a sync context for APScheduler.
    """
    asyncio.run(crawl_and_index())

def start_scheduler():
    """
    Starts the background scheduler.
    """
    scheduler = BackgroundScheduler()
    
    # Schedule daily at 9:00 PM (21:00)
    trigger = CronTrigger(hour=21, minute=0)
    
    scheduler.add_job(
        run_scraper_job,
        trigger=trigger,
        id='daily_scraper',
        name='Daily Web Scraper',
        replace_existing=True
    )
    
    scheduler.start()
    print("[Scheduler] Started. Job scheduled for 21:00 daily.")
    return scheduler
