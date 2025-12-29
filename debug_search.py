from src import search_tool

print("--- Testing Web Search & Scraping ---")
query = "current president of USA"
print(f"Query: {query}")

formatted, sources = search_tool.search_web(query, max_results=3)

print(f"\nFormatted Output Length: {len(formatted)}")
print(f"Number of Sources: {len(sources)}")

for i, source in enumerate(sources):
    print(f"\nSource {i+1}:")
    print(f"Title: {source.get('title')}")
    print(f"URL: {source.get('url')}")
    snippet = source.get('snippet', '')
    content = source.get('content', '')
    print(f"Snippet Length: {len(snippet)}")
    print(f"Content Length: {len(content)}")
    print(f"Content Preview: {content[:100]}...")
