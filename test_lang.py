from duckduckgo_search import DDGS
import re

def contains_cjk(text):
    if not text: return False
    return bool(re.search(r'[\u4e00-\u9fff]', text))

print("--- Testing Language with filtering ---")
query = "current president of USA"
print(f"Query: {query}")

try:
    # Fetch more results to allow for filtering
    results = DDGS().text(query, max_results=10, region="us-en")
    filtered = []
    for r in results:
        title = r.get('title', '')
        snippet = r.get('body', '')
        if not contains_cjk(title) and not contains_cjk(snippet):
            filtered.append(r)
        else:
            print(f"Filtered out: {title}")

    print(f"\nRemaining English Results: {len(filtered)}")
    for r in filtered[:3]:
        print(f"Title: {r.get('title')}")
        print(f"Snippet: {r.get('body')}")
        print("-" * 20)
except Exception as e:
    print(f"Error: {e}")
