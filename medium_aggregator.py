"""
AI Content Aggregator for Medium

This tool collects cybersecurity/AI news from RSS feeds while avoiding detection,
creating ready-to-publish Medium drafts with simple summarization.
"""

import hashlib
import math
import os
import random
import re
import sqlite3
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import frontmatter
import requests
import yaml
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from markdownify import markdownify as md
from readability import Document


class ContentAggregator:
    """Main class with enhanced anti-blocking features."""

    def __init__(self, config_path: str = None):
        """Initialize with configuration."""
        self.config = self.load_config(config_path)
        self.db_conn = self.connect_db()
        self.ensure_dirs()
        self.session = requests.Session()
        self.user_agents = self.load_user_agents()
        self.cookies = {}

    @staticmethod
    def load_config(config_path: str = None) -> dict:
        """Load configuration."""
        default_config = {
            "NICHE": "AI + Cybersecurity news for beginners",
            "SOURCES": [
                "https://feeds.arstechnica.com/arstechnica/technology-lab",
                "https://www.wired.com/feed/category/security/latest/rss",
                "https://www.bleepingcomputer.com/feed/",
                "https://www.schneier.com/feed/",
            ],
            "SOURCE_WEIGHTS": {
                "arstechnica.com": 1.2,
                "wired.com": 1.1,
                "bleepingcomputer.com": 1.0,
                "schneier.com": 1.05,
            },
            "KEYWORDS": {
                "must_have": ["AI", "security", "malware", "ransomware"],
                "nice_to_have": ["beginner", "how to", "guide", "tools"],
                "avoid": ["giveaway", "hiring", "meme"]
            },
            "REQUEST_SETTINGS": {
                "MAX_CONTENT_LENGTH": 200000,
                "MIN_CONTENT_LENGTH": 300,
                "TIMEOUT": 30,
                "THROTTLE_DELAY": 3.0,
                "RETRY_ATTEMPTS": 3,
            },
            "OUTPUT": {
                "TOP_K": 5,
                "OUT_DIR": "drafts",
                "DB_PATH": "state.db",
            },
        }
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                # Deep merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        return default_config

    def load_user_agents(self) -> list:
        """Load rotating user agents from file or use defaults."""
        user_agents_file = Path("user_agents.txt")
        if user_agents_file.exists():
            with open(user_agents_file, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
        ]

    def connect_db(self) -> sqlite3.Connection:
        """Initialize database connection."""
        conn = sqlite3.connect(self.config["OUTPUT"]["DB_PATH"])
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen (
                id TEXT PRIMARY KEY,
                url TEXT UNIQUE,
                added_at TEXT,
                processed BOOLEAN DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS drafts (
                id TEXT PRIMARY KEY,
                url TEXT,
                title TEXT,
                created_at TEXT,
                file_path TEXT,
                published BOOLEAN DEFAULT 0
            )
        """)
        return conn

    def ensure_dirs(self):
        """Ensure output directory exists."""
        Path(self.config["OUTPUT"]["OUT_DIR"]).mkdir(parents=True, exist_ok=True)

    def is_seen(self, url: str) -> bool:
        """Check if URL has been processed before."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        cur = self.db_conn.execute("SELECT 1 FROM seen WHERE id=?", (url_hash,))
        return cur.fetchone() is not None

    def mark_seen(self, url: str, processed: bool = False):
        """Mark URL as seen in database."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        self.db_conn.execute(
            "INSERT OR IGNORE INTO seen(id, url, added_at, processed) VALUES(?, ?, ?, ?)",
            (url_hash, url, datetime.now(timezone.utc).isoformat(), processed)
        )
        self.db_conn.commit()

    @staticmethod
    def domain_of(url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc.replace("www.", "")
        except ValueError:
            return ""

    def safe_get(self, url: str) -> requests.Response:
        """Enhanced HTTP GET with anti-blocking features."""
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "TE": "trailers"
        }

        # Site-specific adjustments
        if "thehackernews.com" in url:
            headers.update({
                "Referer": "https://www.google.com/",
                "Origin": "https://www.google.com"
            })

        for attempt in range(self.config["REQUEST_SETTINGS"]["RETRY_ATTEMPTS"]):
            try:
                # Rotate user agents and add random delays
                headers["User-Agent"] = random.choice(self.user_agents)
                time.sleep(random.uniform(1.0, self.config["REQUEST_SETTINGS"]["THROTTLE_DELAY"]))

                resp = self.session.get(
                    url,
                    headers=headers,
                    cookies=self.cookies,
                    timeout=self.config["REQUEST_SETTINGS"]["TIMEOUT"],
                    allow_redirects=True,
                )

                # Check for soft blocks
                if resp.status_code == 403:
                    raise requests.exceptions.RequestException("403 Forbidden")

                resp.raise_for_status()

                # Check for CAPTCHA pages
                if any(x in resp.text.lower() for x in ["captcha", "cloudflare", "access denied"]):
                    raise requests.exceptions.RequestException("CAPTCHA detected")

                return resp

            except requests.exceptions.RequestException as e:
                if attempt == self.config["REQUEST_SETTINGS"]["RETRY_ATTEMPTS"] - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff

    def parse_date(self, entry) -> datetime:
        """Parse date from feed entry with multiple fallbacks."""
        date_fields = ["published", "updated", "created", "pubDate"]
        for field in date_fields:
            if hasattr(entry, field):
                try:
                    return dateparser.parse(getattr(entry, field))
                except (ValueError, AttributeError):
                    continue
        return datetime.now(timezone.utc)

    def freshness_score(self, dt: datetime) -> float:
        """Calculate freshness score (0.0-1.0)."""
        if not dt:
            return 0.4
        age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return math.exp(-age_hours * math.log(2) / 168)  # 7-day half-life

    def keyword_score(self, text: str) -> float:
        """Score content based on keyword presence."""
        text_lower = text.lower()
        kw = self.config["KEYWORDS"]
        
        if not any(k.lower() in text_lower for k in kw["must_have"]):
            return 0.0
            
        score = 1.0
        score += 0.2 * sum(1 for k in kw["nice_to_have"] if k.lower() in text_lower)
        score -= 0.5 * sum(1 for k in kw["avoid"] if k.lower() in text_lower)
        return max(0.0, min(2.0, score))  # Cap at 2.0

    def rank_item(self, entry: dict) -> float:
        """Score and rank a feed entry."""
        title = entry.get("title", "")
        summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(" ")
        url = entry.get("link", "")
        host = self.domain_of(url)
        dt = self.parse_date(entry)

        text = f"{title}\n\n{summary}"
        ks = self.keyword_score(text)
        fs = self.freshness_score(dt)
        sw = self.config["SOURCE_WEIGHTS"].get(host, 1.0)

        return (0.6 * ks) + (0.3 * fs) + (0.1 * sw)

    def extract_readable(self, url: str) -> dict:
        """Robust content extraction with error handling."""
        try:
            resp = self.safe_get(url)
            
            doc = Document(resp.text)
            title = doc.title() or ""
            soup = BeautifulSoup(doc.summary(), "html.parser")
            
            # Clean content
            for tag in ["script", "style", "nav", "footer", "form", "iframe", "aside"]:
                for element in soup.find_all(tag):
                    element.decompose()
                    
            text = soup.get_text("\n", strip=True)
            text = re.sub(r"\n{3,}", "\n\n", text)
            
            if len(text) < self.config["REQUEST_SETTINGS"]["MIN_CONTENT_LENGTH"]:
                return {"ok": False, "error": "Content too short", "text": text, "title": title}
                
            return {
                "ok": True,
                "title": title,
                "text": text,
                "markdown": md(str(soup)),
                "url": url
            }
            
        except Exception as e:
            return {"ok": False, "error": str(e), "text": "", "title": ""}

    def simple_summarize(self, text: str) -> tuple:
        """Extractive summarization using heuristic methods."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        if len(sentences) < 3:
            return text[:500], text
            
        scored = []
        for i, s in enumerate(sentences):
            score = 1.0 + self.keyword_score(s) - (i / 100)
            scored.append((score, s))
            
        scored.sort(reverse=True, key=lambda x: x[0])
        summary = " ".join([s for _, s in scored[:5]])
        bullets = "\n".join(f"- {s}" for s in [s for _, s in scored[:3]])
        
        return summary, bullets

    def make_draft(self, entry: dict, extracted: dict) -> str:
        """Create polished Medium draft."""
        title = entry.get("title") or extracted.get("title") or "Untitled"
        link = entry.get("link", "")
        domain = self.domain_of(link)
        
        summary, bullets = self.simple_summarize(extracted.get("text", ""))
        
        body = f"""# {title}

**TL;DR**: {summary}

## Key Takeaways
{bullets}

## Full Story
{extracted.get('markdown', extracted.get('text', ''))}

---
*Source: [{domain}]({link}). Automatically summarized for educational purposes.*
"""
        post = frontmatter.Post(body)
        post.metadata.update({
            "title": title,
            "date": datetime.now(timezone.utc).isoformat(),
            "tags": ["AI", "Security", "Tech"],
            "source": domain,
            "status": "draft"
        })
        
        return frontmatter.dumps(post)

    def save_draft(self, content: str, title: str) -> str:
        """Save draft with proper filename."""
        safe_title = re.sub(r'[^\w\s-]', '', title).strip().lower()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)[:50]
        filename = f"{datetime.now().strftime('%Y%m%d')}-{safe_title}.md"
        filepath = Path(self.config["OUTPUT"]["OUT_DIR"]) / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return str(filepath)

    def fetch_candidates(self) -> list:
        """Fetch and parse all feed sources."""
        candidates = []
        
        for source in self.config["SOURCES"]:
            try:
                feed = feedparser.parse(source)
                if feed.bozo and feed.bozo_exception:
                    continue
                    
                for entry in feed.entries:
                    if not entry.get("link"):
                        continue
                        
                    candidates.append({
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", ""),
                        "link": entry.get("link", ""),
                        "entry": entry,
                        "source": source
                    })
                    
            except Exception:
                continue
                
        return candidates

    def process(self):
        """Main processing pipeline."""
        print(f"Starting aggregation for: {self.config['NICHE']}")
        
        candidates = self.fetch_candidates()
        print(f"Found {len(candidates)} candidates")
        
        # Score and filter
        scored = []
        for candidate in candidates:
            if self.is_seen(candidate["link"]):
                continue
                
            try:
                candidate["score"] = self.rank_item(candidate["entry"])
                if candidate["score"] > 0.5:  # Minimum quality threshold
                    scored.append(candidate)
            except Exception:
                continue
                
        # Process top candidates
        scored.sort(key=lambda x: x["score"], reverse=True)
        for i, candidate in enumerate(scored[:self.config["OUTPUT"]["TOP_K"]]):
            print(f"\nProcessing {i+1}/{len(scored[:self.config['OUTPUT']['TOP_K']])}: {candidate['title'][:50]}...")
            
            try:
                time.sleep(random.uniform(1.0, self.config["REQUEST_SETTINGS"]["THROTTLE_DELAY"]))
                extracted = self.extract_readable(candidate["link"])
                
                if not extracted["ok"]:
                    print(f"  ✗ {extracted['error']}")
                    continue
                    
                draft = self.make_draft(candidate, extracted)
                draft_path = self.save_draft(draft, candidate["title"])
                
                self.mark_seen(candidate["link"], processed=True)
                print(f"  ✓ Draft saved: {draft_path}")
                
            except Exception as e:
                print(f"  ! Error: {str(e)}")
                continue
                
        print("\nCompleted processing")


if __name__ == "__main__":
    aggregator = ContentAggregator("config.yaml")
    aggregator.process()