# Web Scraper API - Curl Commands Reference

Use these commands to interact with the API hosted at: `http://159.89.166.91:8002`

## 1. Health Check
Check if the server and the browser instance are running correctly.

```bash
curl http://159.89.166.91:8002/health
```

---

## 1. Search API
Perform a search exploration on Google or Bing. 

**Engines:** `duckduckgo`, or `all`

```bash
curl -X POST http://159.89.166.91:8002/api/search \
     -H "Content-Type: application/json" \
     -d '{
           "query": "artificial intelligence",
           "engine": "duckduckgo"
         }'
```

---

## 2. Scrape API
Extract clean text content and metadata from any public URL.

```bash
curl -X POST http://159.89.166.91:8002/api/scrape \
     -H "Content-Type: application/json" \
     -d '{
           "url": "https://en.wikipedia.org/wiki/Web_scraping"
         }'
```

---

