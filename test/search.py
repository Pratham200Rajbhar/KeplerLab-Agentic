from duckduckgo_search import DDGS

with DDGS() as ddgs:
    results = ddgs.text("Python programming", max_results=5)
    for result in results:
        print(f"Title: {result['title']}")
        print(f"URL: {result['href']}")
        print(f"Snippet: {result['body']}")
        print("-" * 30)
