"""
agents/public_data_agent.py
PublicDataAgent: fetches real-world earned media data for BAMPFA from
Reddit, Google News RSS, NewsAPI, and SerpAPI (Google Reviews).

Each method falls back gracefully to realistic synthetic data when API
credentials are absent or when network/rate-limit errors occur.

Environment variables / Streamlit secrets consumed:
    REDDIT_CLIENT_ID        — Reddit OAuth app client ID
    REDDIT_CLIENT_SECRET    — Reddit OAuth app secret
    REDDIT_USER_AGENT       — e.g. "bampfa-dashboard/1.0"
    NEWSAPI_KEY             — NewsAPI.org key (free tier: ~1 month history)
    SERPAPI_KEY             — SerpAPI key (free tier: 100 searches/month)
                              Used for Google Reviews via google_maps_reviews engine.
                              BAMPFA ludocid: 16873726739869704312

TODO: Add Twitter/X mentions via Academic Research API or snscrape once
      credentials are available.
TODO: Add Instagram mentions via Meta Graph API basic display endpoint.
"""

from __future__ import annotations

import os
import random
import re
import warnings
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Sentiment helper — plain-text, no external NLP library required
# ---------------------------------------------------------------------------

_POSITIVE_WORDS = {
    "amazing", "excellent", "wonderful", "great", "fantastic", "beautiful",
    "stunning", "incredible", "love", "loved", "best", "brilliant", "superb",
    "outstanding", "remarkable", "exceptional", "gorgeous", "inspiring",
    "moving", "perfect", "must-see", "must see", "hidden gem", "underrated",
    "world-class", "world class", "treasure", "recommend", "celebrated",
    "awarded", "praised", "acclaimed", "impressive", "fascinating",
}

_NEGATIVE_WORDS = {
    "bad", "terrible", "awful", "worst", "horrible", "disappointing",
    "disappointed", "disrespectful", "rude", "overpriced", "expensive",
    "crowded", "closed", "broken", "dirty", "boring", "mediocre", "poor",
    "waste", "wasted", "complaint", "complain", "refund", "refused",
    "unfriendly", "chaotic", "disorganized", "cancelled", "cancel",
    "underwhelming", "subpar", "confusing", "unsafe",
}


def _simple_sentiment(text: str, score: int = 0) -> str:
    """
    Returns 'positive', 'neutral', or 'negative' based on keyword scan
    and, for Reddit posts, upvote score.
    """
    if not isinstance(text, str):
        text = ""
    text_lower = text.lower()
    pos = sum(1 for w in _POSITIVE_WORDS if w in text_lower)
    neg = sum(1 for w in _NEGATIVE_WORDS if w in text_lower)
    # Reddit score bonus: high-upvote posts lean positive by community judgment
    if score > 25:
        pos += 2
    elif score < -3:
        neg += 1
    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    return "neutral"


# ---------------------------------------------------------------------------
# Synthetic data generators
# ---------------------------------------------------------------------------

_REDDIT_SUBREDDITS = [
    "berkeley", "bayarea", "movies", "TrueFilm", "criterion", "arthouse", "Art",
]

_REDDIT_TITLES_POSITIVE = [
    "Finally visited BAMPFA — absolutely worth it",
    "BAMPFA's Pacific Film Archive is a hidden gem in the Bay",
    "Just saw the new exhibition at Berkeley Art Museum — stunning",
    "BAMPFA film screening last night was incredible",
    "Highly recommend BAMPFA if you're in the East Bay",
    "Berkeley Art Museum has one of the best film programs in the country",
    "BAMPFA Calder exhibit blew me away",
    "Pacific Film Archive's repertory program is world-class",
    "BAMPFA is criminally underrated — been 3 times this month",
    "Best way to spend a Sunday in Berkeley: BAMPFA and coffee",
]
_REDDIT_TITLES_NEUTRAL = [
    "Anyone been to BAMPFA recently? Worth the trip from SF?",
    "BAMPFA vs SFMOMA — where would you go on a budget?",
    "Question about BAMPFA membership tiers",
    "How early do you need to arrive for Pacific Film Archive screenings?",
    "BAMPFA parking situation — any tips?",
    "Reminder: BAMPFA is free for UC Berkeley students",
    "Is the BAMPFA café still open on Thursdays?",
    "Anyone going to the BAMPFA Godard retrospective?",
    "BAMPFA building designed by Diller Scofidio + Renfro — thoughts?",
    "Pacific Film Archive 35mm screenings coming up this month",
]
_REDDIT_TITLES_NEGATIVE = [
    "Disappointed by the lack of signage at BAMPFA",
    "BAMPFA exhibit felt rushed — not enough context for casual visitors",
    "Parking near BAMPFA is a nightmare",
    "BAMPFA gift shop prices are a bit steep",
    "Wish BAMPFA had longer weekend hours",
]

_NEWS_OUTLETS = [
    "SF Chronicle", "East Bay Times", "Berkeleyside", "KQED Arts",
    "Los Angeles Times", "The Guardian", "Hyperallergic", "ARTnews",
    "The Art Newspaper", "Datebook SF", "Daily Californian", "48hills",
    "SF Weekly", "Bay Area Reporter", "Nob Hill Gazette",
]

_NEWS_TITLES = [
    "BAMPFA Opens Major Survey of Bay Area Conceptual Art",
    "Pacific Film Archive Acquires Rare Kurosawa Print Collection",
    "Berkeley Art Museum Announces 2026 Exhibitions: A Deep Dive",
    "BAMPFA's New Building Wins AIA Award for Cultural Design",
    "Pacific Film Archive Celebrates 55 Years with Free Screening Series",
    "BAMPFA Exhibition Explores the Intersection of Tech and Art",
    "Berkeley Art Museum Expands Free Admission Days for 2026",
    "BAMPFA Receives $2M NEA Grant for Film Preservation",
    "Review: BAMPFA's Calder Retrospective Is a Must-See",
    "Pacific Film Archive Acquires Pioneering Works by Women Directors",
    "BAMPFA Announces Partnership with UC Berkeley Haas School of Business",
    "Berkeley Art Museum Hosts First Major Basquiat Retrospective on West Coast",
    "BAMPFA Director Discusses the Future of Regional Art Museums",
    "Pacific Film Archive's Streaming Service Launches to Rave Reviews",
    "BAMPFA's Education Outreach Reaches 10,000 Bay Area Students",
    "New BAMPFA Gallery Dedicated to Bay Area Photography Opens",
    "Behind the Scenes: How BAMPFA Prepares a Major International Loan Show",
    "BAMPFA Film Series Explores Climate and Environment Through Cinema",
    "Berkeley's BAMPFA Named Among Top 10 US Art Museums by Condé Nast",
    "BAMPFA Announces Free First Friday Events Through 2026",
    "Pacific Film Archive Partners with Criterion Collection for New Series",
    "BAMPFA Exhibit on Japanese American Incarceration Wins National Acclaim",
    "Review: BAMPFA's Hans Hofmann Show Reframes Abstract Expressionism",
    "BAMPFA Announces Spring 2026 Exhibition Lineup",
    "Pacific Film Archive to Screen Restored Print of Akerman's Jeanne Dielman",
    "BAMPFA's Annual Gala Raises Record $1.5M for Programs",
    "Berkeley Art Museum Wins Bay Area Cultural Innovation Award",
    "BAMPFA Exhibition Investigates AI and Creativity",
    "Pacific Film Archive Director on Preserving 20th Century Cinema",
    "BAMPFA to Host Major International Ceramics Survey in 2026",
]

_REVIEW_TEXTS_POSITIVE = [
    "Absolutely brilliant exhibition. The curation was thoughtful and the space is gorgeous.",
    "Best art museum in the Bay Area by a long shot. PFA screenings are world-class.",
    "Visited with my family — kids loved the interactive section. Staff were incredibly welcoming.",
    "BAMPFA never disappoints. The new gallery layout makes so much more sense.",
    "Stunning building, even better collections. Worth every penny of membership.",
    "The Pacific Film Archive screening experience is unlike anything else in the Bay Area.",
    "Went for the first Friday event — great atmosphere, excellent art, reasonable drinks.",
    "The Hans Hofmann collection alone is reason enough to visit. Masterworks everywhere.",
]
_REVIEW_TEXTS_NEUTRAL = [
    "Nice museum, well-organized. Parking can be tricky but that's Berkeley for you.",
    "Good selection of films this month. The seats aren't the most comfortable but the programming is top notch.",
    "Visited on a Tuesday — quiet and relaxed. Would love more interpretive labels on the older works.",
    "Good café, reasonable prices. The exhibit was interesting though a bit small.",
    "Solid museum. Comparable to SFMOMA but more focused on the local scene.",
]
_REVIEW_TEXTS_NEGATIVE = [
    "Felt like the gallery was understaffed. Had trouble finding anyone to ask questions.",
    "Some of the exhibit labels were missing context. Beautiful objects but confusing presentation.",
    "Parking situation is a real challenge. Would appreciate a validated garage.",
]


def _make_date_range(n: int, start: str = "2022-01-01", end: str = "2026-04-30") -> list:
    """Return n random dates between start and end as datetime objects."""
    s = pd.Timestamp(start)
    e = pd.Timestamp(end)
    delta_days = (e - s).days
    offsets = sorted(random.sample(range(delta_days), min(n, delta_days)))
    return [s + timedelta(days=d) for d in offsets]


def _generate_dummy_reddit(n: int = 200) -> pd.DataFrame:
    random.seed(42)
    np.random.seed(42)
    dates = _make_date_range(n)
    rows = []
    for dt in dates:
        sentiment_bucket = random.choices(
            ["positive", "neutral", "negative"], weights=[55, 35, 10]
        )[0]
        if sentiment_bucket == "positive":
            title = random.choice(_REDDIT_TITLES_POSITIVE)
        elif sentiment_bucket == "negative":
            title = random.choice(_REDDIT_TITLES_NEGATIVE)
        else:
            title = random.choice(_REDDIT_TITLES_NEUTRAL)
        score = int(np.random.lognormal(2.5, 1.2)) if sentiment_bucket != "negative" else random.randint(1, 15)
        rows.append({
            "date": dt,
            "subreddit": random.choice(_REDDIT_SUBREDDITS),
            "title": title,
            "score": score,
            "num_comments": random.randint(0, min(score, 80)),
            "url": f"https://www.reddit.com/r/berkeley/comments/dummy_{random.randint(10000,99999)}/",
            "sentiment": sentiment_bucket,
            "source": "reddit_dummy",
        })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.drop_duplicates(subset=["title"]).reset_index(drop=True)


def _generate_dummy_news(n: int = 150) -> pd.DataFrame:
    random.seed(7)
    dates = _make_date_range(n)
    rows = []
    titles_pool = _NEWS_TITLES * 6  # repeat pool so we have enough
    random.shuffle(titles_pool)
    for i, dt in enumerate(dates):
        title = titles_pool[i % len(titles_pool)]
        outlet = random.choice(_NEWS_OUTLETS)
        sentiment = _simple_sentiment(title)
        rows.append({
            "date": dt,
            "title": title,
            "source": outlet,
            "url": f"https://{outlet.lower().replace(' ', '')}.com/bampfa-{random.randint(1000,9999)}",
            "summary": f"{outlet} reports on BAMPFA: {title.lower()}.",
            "sentiment": sentiment,
        })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.drop_duplicates(subset=["url"]).reset_index(drop=True)


def _generate_dummy_reviews(n: int = 80) -> pd.DataFrame:
    random.seed(13)
    dates = _make_date_range(n)
    rows = []
    for dt in dates:
        bucket = random.choices(["positive", "neutral", "negative"], weights=[65, 25, 10])[0]
        if bucket == "positive":
            text = random.choice(_REVIEW_TEXTS_POSITIVE)
            rating = random.choice([4, 5])
        elif bucket == "negative":
            text = random.choice(_REVIEW_TEXTS_NEGATIVE)
            rating = random.choice([1, 2])
        else:
            text = random.choice(_REVIEW_TEXTS_NEUTRAL)
            rating = 3
        rows.append({
            "date": dt,
            "rating": rating,
            "text": text,
            "author": f"Visitor_{random.randint(1000, 9999)}",
            "source": "google_places_dummy",
        })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------------------
# PublicDataAgent
# ---------------------------------------------------------------------------


class PublicDataAgent:
    """
    Fetches public data about BAMPFA from Reddit, Google News RSS, NewsAPI,
    and Google Places. Falls back to realistic synthetic data when credentials
    are absent or when API calls fail.

    Usage:
        agent = PublicDataAgent()
        news_df   = agent.get_all_press_coverage()
        reddit_df = agent.get_reddit_mentions()
        reviews_df = agent.get_google_reviews()
        sentiment  = agent.get_sentiment_summary()
    """

    # Search targets
    REDDIT_SUBREDDITS = [
        "berkeley", "bayarea", "movies", "TrueFilm", "criterion", "arthouse", "Art",
    ]
    REDDIT_SEARCH_TERMS = ["BAMPFA", "Berkeley Art Museum", "Pacific Film Archive"]
    BAMPFA_PLACE_QUERY = "BAMPFA Berkeley Art Museum"

    # BAMPFA's Google Maps location ID — from the Google Maps URL ludocid param
    BAMPFA_LUDOCID = "16873726739869704312"

    def __init__(self):
        self._reddit_client_id     = self._get_secret("REDDIT_CLIENT_ID")
        self._reddit_client_secret = self._get_secret("REDDIT_CLIENT_SECRET")
        self._reddit_user_agent    = self._get_secret("REDDIT_USER_AGENT") or "bampfa-dashboard/1.0"
        self._newsapi_key          = self._get_secret("NEWSAPI_KEY")
        self._serpapi_key          = self._get_secret("SERPAPI_KEY")

    @staticmethod
    def _get_secret(key: str) -> str:
        """Read from env var first, then Streamlit secrets (cloud deployment)."""
        val = os.getenv(key, "")
        if not val:
            try:
                import streamlit as st
                val = st.secrets.get(key, "") or ""
            except Exception:
                pass
        return val

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def get_source_status(self) -> dict[str, str]:
        """Returns dict of source → 'live' | 'demo' for each data source."""
        return {
            "reddit": "live" if (self._reddit_client_id and self._reddit_client_secret) else "demo",
            "google_news_rss": "live",  # no key needed
            "newsapi": "live" if self._newsapi_key else "demo",
            "google_reviews": "live" if self._serpapi_key else "demo",
        }

    # ------------------------------------------------------------------
    # Reddit
    # ------------------------------------------------------------------

    def get_reddit_mentions(self) -> pd.DataFrame:
        """
        Searches configured subreddits for BAMPFA-related posts using PRAW.
        Returns DataFrame: date, subreddit, title, score, num_comments, url,
                           sentiment, source.
        Falls back to synthetic data if credentials are missing or if any
        error occurs.
        """
        if not (self._reddit_client_id and self._reddit_client_secret):
            print("[PublicDataAgent] Reddit: no credentials — returning dummy data")
            return _generate_dummy_reddit()

        try:
            import praw  # type: ignore

            reddit = praw.Reddit(
                client_id=self._reddit_client_id,
                client_secret=self._reddit_client_secret,
                user_agent=self._reddit_user_agent,
            )
            print("[PublicDataAgent] Reddit: fetching live data …")

            rows = []
            seen_ids: set[str] = set()

            for term in self.REDDIT_SEARCH_TERMS:
                for sub_name in self.REDDIT_SUBREDDITS:
                    try:
                        subreddit = reddit.subreddit(sub_name)
                        for post in subreddit.search(term, limit=100, sort="new"):
                            if post.id in seen_ids:
                                continue
                            seen_ids.add(post.id)
                            title = post.title or ""
                            sentiment = _simple_sentiment(title, score=post.score)
                            rows.append({
                                "date": pd.Timestamp.fromtimestamp(post.created_utc),
                                "subreddit": sub_name,
                                "title": title,
                                "score": post.score,
                                "num_comments": post.num_comments,
                                "url": f"https://www.reddit.com{post.permalink}",
                                "sentiment": sentiment,
                                "source": "reddit_live",
                            })
                    except Exception as sub_err:
                        warnings.warn(f"[PublicDataAgent] Reddit sub {sub_name}/{term}: {sub_err}")
                        continue

            if not rows:
                print("[PublicDataAgent] Reddit: zero results — falling back to dummy data")
                return _generate_dummy_reddit()

            df = pd.DataFrame(rows)
            df["date"] = pd.to_datetime(df["date"])
            df = df.drop_duplicates(subset=["url"]).sort_values("date", ascending=False)
            print(f"[PublicDataAgent] Reddit: fetched {len(df)} posts (live)")
            return df.reset_index(drop=True)

        except Exception as e:
            warnings.warn(f"[PublicDataAgent] Reddit error: {e} — falling back to dummy data")
            return _generate_dummy_reddit()

    # ------------------------------------------------------------------
    # Google News RSS  (no API key required)
    # ------------------------------------------------------------------

    def get_news_articles(self) -> pd.DataFrame:
        """
        Parses Google News RSS for BAMPFA-related articles using feedparser.
        No API key required.
        Returns DataFrame: date, title, source, url, summary, sentiment.
        Falls back to synthetic data if feedparser is unavailable or on error.
        """
        feeds = [
            "https://news.google.com/rss/search?q=BAMPFA+%22Berkeley+Art+Museum%22&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=%22Pacific+Film+Archive%22&hl=en-US&gl=US&ceid=US:en",
        ]

        try:
            import feedparser  # type: ignore
        except ImportError:
            warnings.warn("[PublicDataAgent] feedparser not installed — falling back to dummy news")
            df = _generate_dummy_news()
            df["source"] = "google_news_rss_dummy"
            return df

        print("[PublicDataAgent] Google News RSS: fetching live data …")
        rows = []
        seen_urls: set[str] = set()

        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    url = getattr(entry, "link", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # Parse date — feedparser returns a time_struct
                    pub = getattr(entry, "published_parsed", None)
                    if pub:
                        date = pd.Timestamp(*pub[:6])
                    else:
                        date = pd.Timestamp.now()

                    title = getattr(entry, "title", "")
                    summary = getattr(entry, "summary", "")
                    # Google News RSS embeds source in title as "Title - Source"
                    if " - " in title:
                        parts = title.rsplit(" - ", 1)
                        clean_title = parts[0].strip()
                        source = parts[1].strip()
                    else:
                        clean_title = title
                        source = "Google News"

                    rows.append({
                        "date": date,
                        "title": clean_title,
                        "source": source,
                        "url": url,
                        "summary": re.sub(r"<[^>]+>", "", summary),
                        "sentiment": _simple_sentiment(clean_title + " " + summary),
                    })
            except Exception as e:
                warnings.warn(f"[PublicDataAgent] Google News RSS error ({feed_url}): {e}")
                continue

        if not rows:
            print("[PublicDataAgent] Google News RSS: zero results — falling back to dummy data")
            df = _generate_dummy_news()
            df["source_tag"] = "google_news_rss"
            return df

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        df = df.drop_duplicates(subset=["url"]).sort_values("date", ascending=False)
        print(f"[PublicDataAgent] Google News RSS: fetched {len(df)} articles (live)")
        return df.reset_index(drop=True)

    # ------------------------------------------------------------------
    # NewsAPI
    # ------------------------------------------------------------------

    def get_newsapi_articles(self) -> pd.DataFrame:
        """
        Fetches articles mentioning BAMPFA from NewsAPI.org.
        Free tier: ~1 month history, 100 requests/day.
        Returns DataFrame: date, title, source, url, summary, sentiment.
        Falls back to synthetic data if NEWSAPI_KEY is missing or on error.
        """
        if not self._newsapi_key:
            print("[PublicDataAgent] NewsAPI: no key — returning dummy data")
            df = _generate_dummy_news()
            df["source_tag"] = "newsapi_dummy"
            return df

        try:
            from newsapi import NewsApiClient  # type: ignore

            print("[PublicDataAgent] NewsAPI: fetching live data …")
            client = NewsApiClient(api_key=self._newsapi_key)

            query = 'BAMPFA OR "Berkeley Art Museum" OR "Pacific Film Archive"'
            response = client.get_everything(
                q=query,
                language="en",
                sort_by="publishedAt",
                page_size=100,
            )

            articles = response.get("articles", [])
            if not articles:
                print("[PublicDataAgent] NewsAPI: zero results — falling back to dummy data")
                df = _generate_dummy_news()
                df["source_tag"] = "newsapi_dummy"
                return df

            rows = []
            for a in articles:
                title = a.get("title") or ""
                description = a.get("description") or ""
                source_name = (a.get("source") or {}).get("name", "Unknown")
                pub_at = a.get("publishedAt", "")
                try:
                    date = pd.Timestamp(pub_at)
                except Exception:
                    date = pd.Timestamp.now()

                rows.append({
                    "date": date,
                    "title": title,
                    "source": source_name,
                    "url": a.get("url", ""),
                    "summary": description,
                    "sentiment": _simple_sentiment(title + " " + description),
                })

            df = pd.DataFrame(rows)
            df["date"] = pd.to_datetime(df["date"])
            df = df.drop_duplicates(subset=["url"]).sort_values("date", ascending=False)
            print(f"[PublicDataAgent] NewsAPI: fetched {len(df)} articles (live)")
            return df.reset_index(drop=True)

        except Exception as e:
            warnings.warn(f"[PublicDataAgent] NewsAPI error: {e} — falling back to dummy data")
            df = _generate_dummy_news()
            df["source_tag"] = "newsapi_dummy"
            return df

    # ------------------------------------------------------------------
    # Google Reviews (Places API)
    # ------------------------------------------------------------------

    def get_google_reviews(self) -> pd.DataFrame:
        """
        Fetches BAMPFA Google reviews via SerpAPI (google_maps_reviews engine).
        Uses BAMPFA's known ludocid so no place search step is needed.
        SerpAPI free tier: 100 searches/month — sufficient for monthly refresh.
        Paginates up to 5 pages (~50 reviews) to maximise coverage.

        Returns DataFrame: date, rating, text, author, source.
        Falls back to synthetic data if SERPAPI_KEY is missing or on error.
        """
        if not self._serpapi_key:
            print("[PublicDataAgent] SerpAPI: no key — returning dummy reviews")
            return _generate_dummy_reviews()

        try:
            import requests

            print("[PublicDataAgent] SerpAPI: fetching BAMPFA Google reviews …")

            rows = []
            next_page_token = None
            pages_fetched = 0
            max_pages = 5  # cap at 5 API calls on free tier

            while pages_fetched < max_pages:
                params = {
                    "engine": "google_maps_reviews",
                    "ludocid": self.BAMPFA_LUDOCID,
                    "api_key": self._serpapi_key,
                    "hl": "en",
                    "sort_by": "newestFirst",
                }
                if next_page_token:
                    params["next_page_token"] = next_page_token

                resp = requests.get(
                    "https://serpapi.com/search",
                    params=params,
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()

                reviews = data.get("reviews", [])
                if not reviews:
                    break

                for r in reviews:
                    iso_date = r.get("iso_date") or r.get("date", "")
                    try:
                        date = pd.Timestamp(iso_date)
                    except Exception:
                        date = pd.Timestamp.now()

                    text = r.get("snippet", "") or r.get("text", "")
                    user = r.get("user", {})
                    author = user.get("name", "Anonymous") if isinstance(user, dict) else "Anonymous"

                    rows.append({
                        "date": date,
                        "rating": int(r.get("rating", 3)),
                        "text": text,
                        "author": author,
                        "source": "serpapi_google_reviews",
                    })

                pages_fetched += 1
                next_page_token = data.get("serpapi_pagination", {}).get("next_page_token")
                if not next_page_token:
                    break  # no more pages

            if not rows:
                print("[PublicDataAgent] SerpAPI: no reviews returned — falling back to dummy data")
                return _generate_dummy_reviews()

            df = pd.DataFrame(rows)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"])
            print(f"[PublicDataAgent] SerpAPI: fetched {len(df)} Google reviews (live)")
            return df.sort_values("date", ascending=False).reset_index(drop=True)

        except Exception as e:
            warnings.warn(f"[PublicDataAgent] SerpAPI error: {e} — falling back to dummy data")
            return _generate_dummy_reviews()

    # ------------------------------------------------------------------
    # Combined / derived methods
    # ------------------------------------------------------------------

    def get_all_press_coverage(self) -> pd.DataFrame:
        """
        Merges Google News RSS + NewsAPI articles, deduplicates by URL,
        and sorts by date descending.

        For deduplication of near-duplicate titles (same story, different outlet)
        we do a simple normalized-title comparison after stripping punctuation.
        """
        rss = self.get_news_articles()
        api = self.get_newsapi_articles()

        # Ensure consistent columns
        for df in (rss, api):
            for col in ("date", "title", "source", "url", "summary", "sentiment"):
                if col not in df.columns:
                    df[col] = ""

        combined = pd.concat([rss[["date","title","source","url","summary","sentiment"]],
                               api[["date","title","source","url","summary","sentiment"]]],
                              ignore_index=True)

        # Deduplicate by exact URL first
        combined = combined.drop_duplicates(subset=["url"])

        # Soft-dedup: normalize title and remove near-duplicates
        def _normalize(t: str) -> str:
            return re.sub(r"[^a-z0-9 ]", "", str(t).lower()).strip()

        combined["_norm_title"] = combined["title"].apply(_normalize)
        combined = combined.drop_duplicates(subset=["_norm_title"]).drop(columns=["_norm_title"])

        combined["date"] = pd.to_datetime(combined["date"], errors="coerce")
        combined = combined.sort_values("date", ascending=False).reset_index(drop=True)
        return combined

    def get_sentiment_summary(self) -> dict:
        """
        Returns a summary dict with article/post counts broken down by
        sentiment (positive/neutral/negative) and by source type.
        """
        news = self.get_all_press_coverage()
        reddit = self.get_reddit_mentions()
        reviews = self.get_google_reviews()

        summary: dict = {
            "news": {
                "positive": int((news["sentiment"] == "positive").sum()),
                "neutral":  int((news["sentiment"] == "neutral").sum()),
                "negative": int((news["sentiment"] == "negative").sum()),
                "total":    len(news),
            },
            "reddit": {
                "positive": int((reddit["sentiment"] == "positive").sum()),
                "neutral":  int((reddit["sentiment"] == "neutral").sum()),
                "negative": int((reddit["sentiment"] == "negative").sum()),
                "total":    len(reddit),
            },
            "reviews": {
                "avg_rating": round(reviews["rating"].mean(), 2) if len(reviews) else 0.0,
                "total":      len(reviews),
                "5_star":     int((reviews["rating"] == 5).sum()),
                "4_star":     int((reviews["rating"] == 4).sum()),
                "3_star":     int((reviews["rating"] == 3).sum()),
                "2_star":     int((reviews["rating"] == 2).sum()),
                "1_star":     int((reviews["rating"] == 1).sum()),
            },
        }
        return summary

    def get_press_timeline(self) -> pd.DataFrame:
        """
        Returns monthly article counts for use in the Press → Attendance
        correlation analysis.

        Columns: year_month_str, article_count
        """
        news = self.get_all_press_coverage().copy()
        if news.empty:
            # Return empty frame with expected schema
            return pd.DataFrame(columns=["year_month_str", "article_count"])

        news["date"] = pd.to_datetime(news["date"], errors="coerce")
        news = news.dropna(subset=["date"])
        news["year_month"] = news["date"].dt.to_period("M")
        timeline = (
            news.groupby("year_month")
            .size()
            .reset_index(name="article_count")
        )
        timeline["year_month_str"] = timeline["year_month"].astype(str)
        return timeline[["year_month_str", "article_count"]].sort_values("year_month_str")
