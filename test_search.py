from duckduckgo_search import DDGS

def test_query(q):
    print(f"\n--- Testing query: '{q}' with region='us-en' ---")
    try:
        results = DDGS().text(q, max_results=3, region="us-en")
        for r in results:
            print(f"Title: {r.get('title')}\nSnippet: {r.get('body')}\n")
    except Exception as e:
        print(f"Error: {e}")

test_query("president of united states 2025")
test_query("who is the president of USA")
