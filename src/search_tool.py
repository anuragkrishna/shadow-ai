from duckduckgo_search import DDGS
import trafilatura
import concurrent.futures
import re

def contains_cjk(text):
    """
    Checks if the text contains Chinese, Japanese, or Korean characters.
    """
    if not text: return False
    return bool(re.search(r'[\u4e00-\u9fff]', text))

def scrape_content(url: str, max_chars: int = 2000) -> str:
    """
    Scrapes the main text content from a URL using Trafilatura.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return "Failed to download content."
        text = trafilatura.extract(downloaded)
        if not text:
            return "No text extracted."
        return text[:max_chars] + "..." if len(text) > max_chars else text
    except Exception as e:
        return f"Error scraping: {e}"

def search_web(query: str, max_results: int = 5):
    """
    Searches the web using DuckDuckGo, scrapes the top results, and returns formatted context.
    Returns a tuple: (formatted_string, list_of_sources)
    """
    try:
        # region="us-en" improves relevance for English queries
        # Fetch more results to allow for language filtering
        raw_results = DDGS().text(query, max_results=max_results * 3, region="us-en")
        if not raw_results:
            return "No web results found.", []
        
        formatted_results = []
        sources = []
        
        # Filter out non-English (CJK) results
        results = []
        for r in raw_results:
            title = r.get('title', '')
            snippet = r.get('body', '')
            if not contains_cjk(title) and not contains_cjk(snippet):
                results.append(r)
            if len(results) >= max_results:
                break
        
        if not results:
             return "No relevant English results found.", []

        # Helper for parallel scraping
        def process_result(r):
            title = r.get('title', 'No Title')
            link = r.get('href', 'No Link')
            snippet = r.get('body', 'No Content')
            
            # Scrape content
            content = scrape_content(link)
            
            # If scraping failed or returned very little, fallback to snippet
            if not content or len(content) < 50:
                 content = snippet
            
            return {
                "title": title,
                "url": link,
                "snippet": snippet,
                "content": content
            }

        # Scrape in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_url = {executor.submit(process_result, r): r for r in results}
            processed_data = []
            for future in concurrent.futures.as_completed(future_to_url):
                try:
                    data = future.result()
                    processed_data.append(data)
                except Exception as e:
                    print(f"Error processing result: {e}")

        # Format output
        for data in processed_data:
            formatted_results.append(
                f"Title: {data['title']}\nURL: {data['url']}\nSnippet: {data['snippet']}\nFull Content (Scraped): {data['content']}"
            )
            sources.append(data)
            
        return "\n\n".join(formatted_results), sources
    except Exception as e:
        return f"Error searching web: {e}", []
