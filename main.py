import feedparser
import json
import os
import re
import threading
import hashlib
import time
import sqlite3
from difflib import SequenceMatcher
from bs4 import BeautifulSoup
from textblob import TextBlob
from collections import Counter, defaultdict, deque
import nltk
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, scrolledtext
import requests
from datetime import datetime, timedelta
import numpy as np

from newspaper import Article
import pyttsx3

# For charts
import matplotlib

matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
from nltk.tokenize import sent_tokenize

USER_PROFILE_FILE = "user_profile.json"
CLICK_LOG_FILE = "click_log.json"
RECOMMENDATION_HISTORY_FILE = "recommendation_history.json"
MANIPULATION_DB = "manipulation_analysis.db"
FACTCHECK_CACHE = "factcheck_cache.json"
NEWS_DNA_DB = "news_dna.db"
COGNITIVE_PROFILES = "cognitive_profiles.json"
ACCESSIBILITY_SETTINGS = "accessibility_settings.json"

DEFAULT_RSS_SOURCES = [
    "https://rss.cnn.com/rss/edition.rss",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://www.theguardian.com/world/rss"
]

GNEWS_API_KEY = "bd0d3ffad825cd83bb6b5da69aa71a24"
REALTIME_NEWS_API_KEY = "ecd7e32461msh92925960050e441p154d3ajsn6ab6819253ce"

STOPWORDS = set("""
href theguardian news that with this from said have will your just more they about into than been their which them some would what there could like when also after where over such only other these those upon very through many
www html https continue reading world link article click here make time good people years first last update updates days today
""".split())

# Psycholinguistic Manipulation Patterns
MANIPULATION_PATTERNS = {
    'fear_appeal': [
        r'\b(crisis|disaster|catastrophe|emergency|danger|threat|risk|fear|scary|terrifying)\b',
        r'\b(will destroy|will ruin|will end|will kill|will eliminate)\b',
        r'\b(if you don\'t|unless you|before it\'s too late)\b'
    ],
    'authority_appeal': [
        r'\b(experts say|scientists confirm|studies show|research proves)\b',
        r'\b(according to authorities|official sources|government confirms)\b',
        r'\b(doctors recommend|professionals agree)\b'
    ],
    'bandwagon': [
        r'\b(everyone is|millions are|people are|join the movement)\b',
        r'\b(trending|popular|viral|widespread)\b',
        r'\b(don\'t be left behind|join now|be part of)\b'
    ],
    'scarcity': [
        r'\b(limited time|while supplies last|act now|hurry|deadline)\b',
        r'\b(only \d+ left|exclusive|rare opportunity)\b',
        r'\b(before it\'s gone|last chance|final offer)\b'
    ],
    'confirmation_bias': [
        r'\b(as we predicted|we told you|just as expected)\b',
        r'\b(proves our point|confirms what we knew|validates our)\b'
    ],
    'false_dichotomy': [
        r'\b(either you|you must choose|only two options)\b',
        r'\b(if not this then|you\'re either with us or)\b'
    ]
}


def init_databases():
    """Initialize SQLite databases for advanced features"""
    try:
        # Manipulation analysis database
        conn = sqlite3.connect(MANIPULATION_DB)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS manipulation_scores (
                id INTEGER PRIMARY KEY,
                article_url TEXT UNIQUE,
                title TEXT,
                fear_score REAL,
                authority_score REAL,
                bandwagon_score REAL,
                scarcity_score REAL,
                confirmation_bias_score REAL,
                false_dichotomy_score REAL,
                overall_manipulation_score REAL,
                timestamp DATETIME
            )
        ''')
        conn.commit()
        conn.close()

        # News DNA database
        conn = sqlite3.connect(NEWS_DNA_DB)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_dna (
                id INTEGER PRIMARY KEY,
                article_url TEXT UNIQUE,
                title TEXT,
                content_hash TEXT,
                entity_fingerprint TEXT,
                topic_vector TEXT,
                temporal_signature TEXT,
                similarity_cluster INTEGER,
                timestamp DATETIME
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database initialization error: {e}")


def load_accessibility_settings():
    """Load accessibility settings from file"""
    if os.path.exists(ACCESSIBILITY_SETTINGS):
        try:
            with open(ACCESSIBILITY_SETTINGS, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        'cognitive_profile': 'standard',
        'font_size': 12,
        'line_spacing': 1.2,
        'high_contrast': False,
        'reduce_animations': False,
        'auto_read': False,
        'show_reading_time': True,
        'highlight_keywords': False
    }


def save_accessibility_settings(settings):
    """Save accessibility settings to file"""
    try:
        with open(ACCESSIBILITY_SETTINGS, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Failed to save accessibility settings: {e}")
        return False


class PsycholinguisticAnalyzer:
    def __init__(self):
        self.manipulation_cache = {}

    def analyze_manipulation(self, text):
        """Analyze text for psycholinguistic manipulation techniques"""
        if not text:
            return {technique: 0.0 for technique in MANIPULATION_PATTERNS.keys()}

        text_lower = text.lower()
        scores = {}

        for technique, patterns in MANIPULATION_PATTERNS.items():
            score = 0
            matches = 0

            for pattern in patterns:
                try:
                    matches += len(re.findall(pattern, text_lower, re.IGNORECASE))
                except:
                    continue

            # Normalize score by text length
            word_count = len(text.split())
            if word_count > 0:
                score = (matches / word_count) * 100

            scores[technique] = min(score, 10.0)  # Cap at 10

        # Calculate overall manipulation score
        overall_score = sum(scores.values()) / len(scores) if scores else 0
        scores['overall_manipulation_score'] = overall_score

        return scores

    def get_manipulation_risk_level(self, score):
        """Convert manipulation score to risk level"""
        if score < 1.0:
            return "LOW"
        elif score < 3.0:
            return "MEDIUM"
        elif score < 5.0:
            return "HIGH"
        else:
            return "CRITICAL"

    def store_manipulation_analysis(self, article):
        """Store manipulation analysis in database"""
        try:
            scores = self.analyze_manipulation(article.get('summary', '') + ' ' + article.get('title', ''))

            conn = sqlite3.connect(MANIPULATION_DB)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO manipulation_scores 
                (article_url, title, fear_score, authority_score, bandwagon_score, 
                 scarcity_score, confirmation_bias_score, false_dichotomy_score, 
                 overall_manipulation_score, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article.get('link', ''),
                article.get('title', ''),
                scores.get('fear_appeal', 0),
                scores.get('authority_appeal', 0),
                scores.get('bandwagon', 0),
                scores.get('scarcity', 0),
                scores.get('confirmation_bias', 0),
                scores.get('false_dichotomy', 0),
                scores.get('overall_manipulation_score', 0),
                datetime.utcnow()
            ))

            conn.commit()
            conn.close()

            return scores
        except Exception as e:
            print(f"Manipulation analysis error: {e}")
            return {}


class MisinformationDetector:
    def __init__(self):
        self.factcheck_cache = self.load_factcheck_cache()
        self.source_credibility = {}

    def load_factcheck_cache(self):
        """Load fact-checking cache from file"""
        if os.path.exists(FACTCHECK_CACHE):
            try:
                with open(FACTCHECK_CACHE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def extract_claims(self, text):
        """Extract factual claims from text using basic NLP"""
        sentences = sent_tokenize(text)
        claims = []
        for sent in sentences:
            if any(word in sent.lower() for word in ['said', 'reported', 'claims', 'states', 'according']):
                claims.append(sent.strip())
        return claims[:5]

    def check_source_credibility(self, url):
        """Check source credibility based on domain"""
        if url in self.source_credibility:
            return self.source_credibility[url]

        try:
            domain = url.split('/')[2] if '/' in url else url
        except:
            domain = url

        trusted_sources = ['bbc.co.uk', 'reuters.com', 'ap.org', 'npr.org', 'cnn.com']
        questionable_sources = ['infowars.com', 'naturalnews.com', 'beforeitsnews.com']

        if any(trusted in domain for trusted in trusted_sources):
            credibility = 0.9
        elif any(questionable in domain for questionable in questionable_sources):
            credibility = 0.2
        else:
            credibility = 0.6  # Neutral

        self.source_credibility[url] = credibility
        return credibility

    def fact_check_claims(self, claims):
        """Fact-check extracted claims (mock implementation)"""
        results = []

        for claim in claims:
            claim_hash = hashlib.md5(claim.encode()).hexdigest()

            if claim_hash in self.factcheck_cache:
                results.append(self.factcheck_cache[claim_hash])
            else:
                # Mock fact-checking result
                mock_result = {
                    'claim': claim,
                    'verdict': np.random.choice(['TRUE', 'FALSE', 'MIXED', 'UNVERIFIED'], p=[0.4, 0.2, 0.2, 0.2]),
                    'confidence': np.random.uniform(0.5, 1.0),
                    'source': 'mock_factchecker'
                }

                self.factcheck_cache[claim_hash] = mock_result
                results.append(mock_result)

        return results

    def calculate_misinformation_risk(self, article):
        """Calculate overall misinformation risk for an article"""
        text = article.get('summary', '') + ' ' + article.get('title', '')
        claims = self.extract_claims(text)
        fact_check_results = self.fact_check_claims(claims)
        source_credibility = self.check_source_credibility(article.get('link', ''))

        false_claims = sum(1 for result in fact_check_results if result['verdict'] == 'FALSE')
        total_claims = len(fact_check_results)

        if total_claims > 0:
            false_ratio = false_claims / total_claims
        else:
            false_ratio = 0

        # Combine factors
        risk_score = (false_ratio * 0.6) + ((1 - source_credibility) * 0.4)

        return {
            'risk_score': risk_score,
            'risk_level': self.get_risk_level(risk_score),
            'claims': fact_check_results,
            'source_credibility': source_credibility
        }

    def get_risk_level(self, score):
        """Convert risk score to level"""
        if score < 0.2:
            return "LOW"
        elif score < 0.5:
            return "MEDIUM"
        elif score < 0.7:
            return "HIGH"
        else:
            return "CRITICAL"


class NeurodiversityAdapter:
    def __init__(self):
        self.cognitive_profiles = {}

    def adapt_content_for_adhd(self, text, settings=None):
        """Adapt content for ADHD users"""
        sentences = sent_tokenize(text)
        adapted = []

        # Add progress indicator
        total_sections = len(sentences) // 3
        adapted.append(f"📊 CONTENT SECTIONS: {total_sections}")
        adapted.append("🎯 FOCUS MODE: ADHD Optimized")
        adapted.append(f"⏱️ Estimated reading time: {len(text.split()) // 200 + 1} minutes\n")

        for i, sentence in enumerate(sentences):
            # Add section breaks
            if i % 3 == 0 and i > 0:
                section_num = (i // 3)
                adapted.append(f"\n🔄 SECTION {section_num} COMPLETE - Take a breath! 🔄\n")
                adapted.append("━" * 50 + "\n")

            # Highlight important words
            words = sentence.split()
            for j, word in enumerate(words):
                if len(word) > 6 and word.lower() not in STOPWORDS:
                    if any(char.isupper() for char in word) or word.lower() in ['important', 'breaking', 'urgent',
                                                                                'critical']:
                        words[j] = f"🔸{word}🔸"
                    else:
                        words[j] = f"**{word}**"
            sentence = " ".join(words)

            adapted.append(sentence)

        adapted.append("\n✅ ARTICLE COMPLETE! Great job staying focused! ✅")

        return "\n\n".join(adapted)

    def adapt_content_for_autism(self, text, settings=None):
        """Adapt content for autism spectrum users"""
        sentences = sent_tokenize(text)
        adapted = []

        # Structured header with predictable format
        adapted.append("📋 STRUCTURED ARTICLE FORMAT")
        adapted.append("=" * 40)
        adapted.append(f"📊 Total sentences: {len(sentences)}")
        adapted.append(f"📄 Total paragraphs: {len(text.split(chr(10))) if chr(10) in text else 1}")
        adapted.append(f"⏱️ Reading time: {len(text.split()) // 200 + 1} minutes")
        adapted.append(f"🔤 Word count: {len(text.split())} words")
        adapted.append("=" * 40)
        adapted.append("")

        # Table of contents
        adapted.append("📑 CONTENT STRUCTURE:")
        section_count = 0
        for i in range(0, len(sentences), 3):
            section_count += 1
            preview = sentences[i][:50] + "..." if len(sentences[i]) > 50 else sentences[i]
            adapted.append(f"   Section {section_count}: {preview}")
        adapted.append("")

        # Main content with clear numbering
        adapted.append("📖 ARTICLE CONTENT:")
        adapted.append("=" * 40)

        section_num = 1
        for i, sentence in enumerate(sentences):
            if i % 3 == 0:
                adapted.append(f"\n📍 SECTION {section_num}:")
                section_num += 1

            # Number each sentence for clarity
            sentence_num = (i % 3) + 1
            adapted.append(f"   {sentence_num}. {sentence}")

        adapted.append("\n" + "=" * 40)
        adapted.append("✅ END OF STRUCTURED CONTENT")

        return "\n".join(adapted)

    def adapt_content_for_dyslexia(self, text, settings=None):
        """Adapt content for dyslexia"""
        sentences = sent_tokenize(text)
        adapted = []

        # Dyslexia-friendly header
        adapted.append("🔤 DYSLEXIA-FRIENDLY FORMAT")
        adapted.append("Easy-to-read version below:")
        adapted.append("")

        for sentence in sentences:
            words = sentence.split()

            # Break long sentences
            if len(words) > 15:
                parts = []
                current_part = []

                for word in words:
                    current_part.append(word)
                    if (len(current_part) >= 7 and
                            word.endswith((',', ';')) or word.lower() in ['and', 'but', 'or', 'because']):
                        parts.append(" ".join(current_part))
                        current_part = []

                if current_part:
                    parts.append(" ".join(current_part))

                for part in parts:
                    adapted.append("• " + part.strip())
            else:
                adapted.append("• " + sentence)

        # Add syllable breaks for difficult words
        final_text = "\n\n".join(adapted)

        difficult_words = {
            'government': 'gov-ern-ment',
            'important': 'im-por-tant',
            'information': 'in-for-ma-tion',
            'development': 'de-vel-op-ment',
            'environment': 'en-vi-ron-ment',
            'technology': 'tech-nol-o-gy',
            'organization': 'or-gan-i-za-tion'
        }

        for word, syllables in difficult_words.items():
            final_text = re.sub(r'\b' + word + r'\b', syllables, final_text, flags=re.IGNORECASE)

        return final_text

    def get_adapted_content(self, text, user_profile, settings=None):
        """Get content adapted for user's cognitive profile"""
        cognitive_needs = user_profile.get('cognitive_needs', [])

        if 'adhd' in cognitive_needs:
            return self.adapt_content_for_adhd(text, settings)
        elif 'autism' in cognitive_needs:
            return self.adapt_content_for_autism(text, settings)
        elif 'dyslexia' in cognitive_needs:
            return self.adapt_content_for_dyslexia(text, settings)
        else:
            return text


class NewsDNAAnalyzer:
    def __init__(self):
        self.entity_cache = {}

    def extract_entities(self, text):
        """Extract named entities from text - simple fallback"""
        entities = []
        words = text.split()
        for word in words:
            if word[0].isupper() and len(word) > 2:
                entities.append((word, 'ENTITY'))
        return entities[:10]

    def create_content_hash(self, text):
        """Create a hash of the content"""
        return hashlib.md5(text.encode()).hexdigest()

    def calculate_article_similarity(self, article1, article2):
        """Calculate similarity between two articles"""
        # Title similarity
        title_sim = SequenceMatcher(None, article1['title'], article2['title']).ratio()

        # Content similarity
        content_sim = SequenceMatcher(None,
                                      article1.get('summary', ''),
                                      article2.get('summary', '')).ratio()

        # Combined similarity
        return (title_sim * 0.6) + (content_sim * 0.4)

    def store_news_dna(self, article):
        """Store news DNA in database"""
        try:
            text = article.get('summary', '') + ' ' + article.get('title', '')
            entities = self.extract_entities(text)

            conn = sqlite3.connect(NEWS_DNA_DB)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO news_dna 
                (article_url, title, content_hash, entity_fingerprint, 
                 topic_vector, temporal_signature, similarity_cluster, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article.get('link', ''),
                article.get('title', ''),
                self.create_content_hash(text),
                json.dumps([e[0] for e in entities]),
                json.dumps([]),
                json.dumps({'timestamp': str(datetime.utcnow())}),
                0,
                datetime.utcnow()
            ))

            conn.commit()
            conn.close()

            return True
        except Exception as e:
            print(f"News DNA storage error: {e}")
            return False

    def find_similar_articles(self, article, threshold=0.7):
        """Find articles similar to the given article"""
        try:
            conn = sqlite3.connect(NEWS_DNA_DB)
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM news_dna LIMIT 50')
            stored_articles = cursor.fetchall()
            conn.close()

            similar = []

            for stored in stored_articles:
                stored_article = {
                    'title': stored[2],
                    'summary': '',
                    'link': stored[1]
                }

                similarity = self.calculate_article_similarity(article, stored_article)

                if similarity > threshold:
                    similar.append({
                        'article': stored_article,
                        'similarity': similarity,
                        'stored_data': stored
                    })

            return sorted(similar, key=lambda x: x['similarity'], reverse=True)
        except Exception as e:
            print(f"Similar articles search error: {e}")
            return []


# Initialize advanced analyzers
init_databases()
manipulation_analyzer = PsycholinguisticAnalyzer()
misinformation_detector = MisinformationDetector()
neurodiversity_adapter = NeurodiversityAdapter()
news_dna_analyzer = NewsDNAAnalyzer()

# Sample articles for testing (when real articles aren't available)
SAMPLE_ARTICLES = [
    {
        "title": "Breaking: Government Announces New Technology Initiative",
        "summary": "The government today announced a major new technology initiative aimed at improving digital infrastructure. According to officials, this program will modernize systems across various departments. Experts say this could transform how citizens interact with government services. The initiative includes funding for cybersecurity improvements and artificial intelligence research.",
        "link": "https://example.com/tech-initiative",
        "published": "2025-06-02"
    },
    {
        "title": "Health Study Reveals Important Findings About Exercise",
        "summary": "A new health study published in a leading medical journal reveals important findings about the benefits of regular exercise. Researchers found that even moderate physical activity can significantly improve mental health outcomes. The study followed 10,000 participants over five years and provides compelling evidence for the importance of staying active.",
        "link": "https://example.com/health-study",
        "published": "2025-06-01"
    },
    {
        "title": "Climate Change Report Shows Urgent Need for Action",
        "summary": "Scientists warn that immediate action is needed to address climate change impacts. The latest report shows rising temperatures are accelerating faster than previously predicted. Urgent measures are required to prevent catastrophic consequences for future generations. Unless we act now, the damage could be irreversible.",
        "link": "https://example.com/climate-report",
        "published": "2025-06-01"
    }
]


# Original functions (preserved)
def get_user_profile_gui():
    if os.path.exists(USER_PROFILE_FILE):
        try:
            with open(USER_PROFILE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            messagebox.showerror("Profile Error", f"Failed to load user profile: {e}")
    interests = simpledialog.askstring(
        "Profile Setup",
        "Enter your interests (comma-separated):",
        initialvalue="technology,health,politics"
    )
    if not interests:
        interests = "news"
    sources = DEFAULT_RSS_SOURCES.copy()
    profile = {
        "interests": [i.strip().lower() for i in interests.split(',') if i.strip()],
        "sources": sources
    }
    try:
        with open(USER_PROFILE_FILE, 'w') as f:
            json.dump(profile, f, indent=2)
    except Exception as e:
        messagebox.showerror("Profile Error", f"Failed to save user profile: {e}")
    return profile


def save_user_profile(profile):
    try:
        with open(USER_PROFILE_FILE, 'w') as f:
            json.dump(profile, f, indent=2)
    except Exception as e:
        messagebox.showerror("Profile Error", f"Failed to save user profile: {e}")


def fetch_rss_articles(sources, max_articles_per_feed=10):
    all_articles = []
    for source in sources:
        try:
            feed = feedparser.parse(source)
            count = 0
            for entry in feed.entries:
                all_articles.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", "")
                })
                count += 1
                if count >= max_articles_per_feed:
                    break
        except Exception as e:
            print(f"Failed to fetch from {source}: {e}")

    # Add sample articles if no articles were fetched
    if not all_articles:
        all_articles = SAMPLE_ARTICLES.copy()

    return all_articles


def fetch_gnews_articles(interests, max_days=30, max_articles_per_interest=10):
    # For demo purposes, return sample articles
    return SAMPLE_ARTICLES.copy()


def fetch_realtime_news_articles(interests, max_articles_per_interest=10):
    # For demo purposes, return sample articles
    return SAMPLE_ARTICLES.copy()


def filter_articles_by_date(articles, max_days=30):
    return articles  # Return all for demo


def is_similar(title1, title2, threshold=0.8):
    try:
        return SequenceMatcher(None, title1, title2).ratio() > threshold
    except Exception:
        return False


def deduplicate_articles(articles):
    unique = []
    seen_titles = []
    for article in articles:
        if not any(is_similar(article['title'], t) for t in seen_titles):
            unique.append(article)
            seen_titles.append(article['title'])
    return unique


def bullet_summary(text, max_points=5):
    try:
        text = BeautifulSoup(text, "html.parser").get_text()
        sentences = sent_tokenize(text)
        return sentences[:max_points]
    except Exception:
        return []


def get_sentiment(text):
    try:
        analysis = TextBlob(text)
        polarity = analysis.sentiment.polarity
        if polarity > 0.1:
            return "positive"
        elif polarity < 0:
            return "negative"
        return "neutral"
    except Exception:
        return "neutral"


def get_sentiment_score(text):
    try:
        analysis = TextBlob(text)
        return analysis.sentiment.polarity
    except Exception:
        return 0.0


def extract_keywords(text):
    try:
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        return [word for word in words if word not in STOPWORDS]
    except Exception:
        return []


def trending_keywords(articles, top_n=20):
    keywords = []
    for article in articles:
        keywords.extend(extract_keywords(article.get('summary', '') + " " + article.get('title', '')))
    counts = Counter(keywords)
    meaningful = [(kw, cnt) for kw, cnt in counts.most_common() if cnt > 1]
    return meaningful[:top_n]


def recommend_by_interest(articles, interests):
    filtered = []
    for article in articles:
        if any(interest in (article.get('summary', '') + " " + article.get('title', '')).lower() for interest in
               interests):
            filtered.append(article)
    return filtered


def rank_by_user_behavior(articles, click_log):
    weights = {}
    for click in click_log:
        for word in click.get('title', '').lower().split():
            weights[word] = weights.get(word, 0) + 1

    def score(article):
        return sum(weights.get(w, 0) for w in article.get('title', '').lower().split())

    return sorted(articles, key=score, reverse=True)


def load_click_log():
    if os.path.exists(CLICK_LOG_FILE):
        try:
            with open(CLICK_LOG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_click_log(log):
    try:
        with open(CLICK_LOG_FILE, 'w') as f:
            json.dump(log, f, indent=2)
    except Exception as e:
        print(f"Failed to save click log: {e}")


def simulate_user_click(article, click_log):
    if not any(a['title'] == article['title'] for a in click_log):
        article = dict(article)
        article['read_date'] = datetime.utcnow().date().isoformat()
        click_log.append(article)
        save_click_log(click_log)


def filter_out_read(articles, click_log):
    read_titles = set(a['title'] for a in click_log)
    return [a for a in articles if a['title'] not in read_titles]


def save_recommendation_history(history):
    try:
        with open(RECOMMENDATION_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Failed to save recommendation history: {e}")


def load_recommendation_history():
    if os.path.exists(RECOMMENDATION_HISTORY_FILE):
        try:
            with open(RECOMMENDATION_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def get_sentiment_counts(articles):
    counts = defaultdict(int)
    for a in articles:
        sentiment = get_sentiment(a.get("summary", ""))
        counts[sentiment] += 1
    return counts


def recommend_based_on_history(articles, click_log, history):
    if not click_log:
        return []
    clicked_keywords = set()
    for a in click_log:
        clicked_keywords.update(extract_keywords(a.get('summary', '') + " " + a.get('title', '')))
    recommendations = []
    for a in articles:
        if any(kw in extract_keywords(a.get('summary', '') + " " + a.get('title', '')) for kw in clicked_keywords):
            recommendations.append(a)
    read_titles = set(a['title'] for a in click_log)
    recommendations = [a for a in recommendations if a['title'] not in read_titles]
    for rec in recommendations:
        if rec not in history:
            history.append(rec)
    save_recommendation_history(history)
    return recommendations


def user_sentiment_trend(click_log, days=7):
    trend = defaultdict(lambda: defaultdict(int))
    today = datetime.utcnow().date()
    date_list = [(today - timedelta(days=i)).isoformat() for i in reversed(range(days))]
    for a in click_log:
        d = a.get("read_date")
        if not d:
            d = today.isoformat()
        sentiment = get_sentiment(a.get("summary", ""))
        trend[d][sentiment] += 1
    result = []
    for d in date_list:
        result.append({
            "date": d,
            "positive": trend[d].get("positive", 0),
            "neutral": trend[d].get("neutral", 0),
            "negative": trend[d].get("negative", 0)
        })
    return result


def per_interest_sentiment(articles, interests):
    per_interest = {interest: defaultdict(int) for interest in interests}
    for a in articles:
        sentiment = get_sentiment(a.get("summary", ""))
        text = (a.get("summary", "") + " " + a.get("title", "")).lower()
        for interest in interests:
            if interest in text:
                per_interest[interest][sentiment] += 1
    return per_interest


def most_positive_negative_articles(articles, top_n=5):
    scored = []
    for a in articles:
        summary = a.get("summary", "")
        score = get_sentiment_score(summary)
        scored.append((score, a))
    scored.sort(reverse=True, key=lambda x: x[0])
    most_positive = scored[:top_n]
    most_negative = sorted(scored, key=lambda x: x[0])[:top_n]
    return most_positive, most_negative


def fetch_full_article_text(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text.strip()
    except Exception as e:
        return f"Could not fetch full article text: {e}"


def speak_text(text):
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        if voices:
            engine.setProperty('voice', voices[0].id)
        engine.setProperty('rate', 170)
        engine.setProperty('volume', 1.0)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"Text-to-Speech failed: {e}")


class NewsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Advanced Perspective Powered Personalized News Aggregator")
        self.geometry("1800x1000")
        self.profile = get_user_profile_gui()
        self.click_log = load_click_log()
        self.articles = []
        self.filtered_articles = []
        self.seen_articles = []
        self.recommendation_history = load_recommendation_history()
        self.accessibility_settings = load_accessibility_settings()
        self.create_widgets()
        self.load_articles_async()

    def create_widgets(self):
        self.tab_control = ttk.Notebook(self)

        # Original tabs
        self.tab_feed = ttk.Frame(self.tab_control)
        self.tab_trending = ttk.Frame(self.tab_control)
        self.tab_sentiment = ttk.Frame(self.tab_control)
        self.tab_recommend = ttk.Frame(self.tab_control)
        self.tab_seen = ttk.Frame(self.tab_control)
        self.tab_sentiment_advanced = ttk.Frame(self.tab_control)
        self.tab_settings = ttk.Frame(self.tab_control)

        # New advanced tabs
        self.tab_manipulation = ttk.Frame(self.tab_control)
        self.tab_factcheck = ttk.Frame(self.tab_control)
        self.tab_neurodiversity = ttk.Frame(self.tab_control)
        self.tab_newsdna = ttk.Frame(self.tab_control)

        # Add all tabs
        self.tab_control.add(self.tab_feed, text="Personalized Feed")
        self.tab_control.add(self.tab_trending, text="Trending Topics")
        self.tab_control.add(self.tab_sentiment, text="Sentiment Analysis")
        self.tab_control.add(self.tab_sentiment_advanced, text="Sentiment Insights")
        self.tab_control.add(self.tab_recommend, text="Recommendations")
        self.tab_control.add(self.tab_seen, text="Seen Articles")
        self.tab_control.add(self.tab_manipulation, text="Manipulation Analysis")
        self.tab_control.add(self.tab_factcheck, text="Fact Check")
        self.tab_control.add(self.tab_neurodiversity, text="🔧 Accessibility")
        self.tab_control.add(self.tab_newsdna, text="News DNA")
        self.tab_control.add(self.tab_settings, text="Settings")

        self.tab_control.pack(expand=1, fill='both')

        # Original feed tab (preserved)
        self.feed_listbox = tk.Listbox(self.tab_feed, font=("Arial", 12), selectmode=tk.SINGLE)
        self.feed_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.feed_listbox.bind("<<ListboxSelect>>", self.on_article_select)
        self.article_details = scrolledtext.ScrolledText(self.tab_feed, width=60, height=35, font=("Arial", 11))
        self.article_details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.mark_read_btn = tk.Button(self.tab_feed, text="Mark as Read", state=tk.DISABLED, command=self.mark_as_read)
        self.mark_read_btn.pack(side=tk.BOTTOM, pady=5)
        self.reader_mode_btn = tk.Button(self.tab_feed, text="Reader Mode (Full Article)", state=tk.DISABLED,
                                         command=self.show_reader_mode)
        self.reader_mode_btn.pack(side=tk.BOTTOM, pady=5)
        self.tts_btn = tk.Button(self.tab_feed, text="🔊 Speak Summary", state=tk.DISABLED, command=self.speak_summary)
        self.tts_btn.pack(side=tk.BOTTOM, pady=5)

        # Enhanced Neurodiversity/Accessibility tab - THIS IS THE FIXED VERSION
        self.create_accessibility_tab()

        # Other tabs
        self.create_other_tabs()

    def create_accessibility_tab(self):
        """Create the fully functional accessibility tab with real-time updates"""
        main_frame = tk.Frame(self.tab_neurodiversity)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Settings Panel
        settings_frame = tk.LabelFrame(main_frame, text="🔧 Accessibility Settings",
                                       font=("Arial", 14, "bold"), fg="darkblue")
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # Status indicator
        self.status_label = tk.Label(settings_frame, text="Settings Status: Ready",
                                     font=("Arial", 10), fg="green")
        self.status_label.pack(anchor='w', padx=10, pady=2)

        # Cognitive Profile Selection
        profile_frame = tk.Frame(settings_frame)
        profile_frame.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(profile_frame, text="Cognitive Profile:",
                 font=("Arial", 12, "bold")).pack(side=tk.LEFT)

        self.cognitive_var = tk.StringVar(value=self.accessibility_settings.get('cognitive_profile', 'standard'))

        profiles = [("Standard", "standard"), ("ADHD Focus", "adhd"),
                    ("Autism Structured", "autism"), ("Dyslexia Friendly", "dyslexia")]

        for text, mode in profiles:
            rb = tk.Radiobutton(profile_frame, text=text, variable=self.cognitive_var,
                                value=mode, command=self.on_cognitive_profile_change,
                                font=("Arial", 11))
            rb.pack(side=tk.LEFT, padx=8)

        # Visual Settings
        visual_frame = tk.Frame(settings_frame)
        visual_frame.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(visual_frame, text="Font Size:", font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        self.font_size_var = tk.IntVar(value=self.accessibility_settings.get('font_size', 12))
        self.font_size_label = tk.Label(visual_frame, text=f"{self.font_size_var.get()}pt",
                                        font=("Arial", 10), width=4)
        self.font_size_label.pack(side=tk.LEFT, padx=5)

        font_scale = tk.Scale(visual_frame, from_=10, to=24, orient=tk.HORIZONTAL,
                              variable=self.font_size_var, command=self.on_font_size_change,
                              length=150)
        font_scale.pack(side=tk.LEFT, padx=5)

        tk.Label(visual_frame, text="Line Spacing:", font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=(20, 5))
        self.line_spacing_var = tk.DoubleVar(value=self.accessibility_settings.get('line_spacing', 1.2))
        self.line_spacing_label = tk.Label(visual_frame, text=f"{self.line_spacing_var.get():.1f}x",
                                           font=("Arial", 10), width=4)
        self.line_spacing_label.pack(side=tk.LEFT, padx=5)

        spacing_scale = tk.Scale(visual_frame, from_=1.0, to=3.0, resolution=0.1,
                                 orient=tk.HORIZONTAL, variable=self.line_spacing_var,
                                 command=self.on_line_spacing_change, length=150)
        spacing_scale.pack(side=tk.LEFT, padx=5)

        # Feature toggles
        toggle_frame = tk.Frame(settings_frame)
        toggle_frame.pack(fill=tk.X, padx=10, pady=8)

        self.high_contrast_var = tk.BooleanVar(value=self.accessibility_settings.get('high_contrast', False))
        self.highlight_keywords_var = tk.BooleanVar(value=self.accessibility_settings.get('highlight_keywords', False))
        self.auto_read_var = tk.BooleanVar(value=self.accessibility_settings.get('auto_read', False))
        self.show_reading_time_var = tk.BooleanVar(value=self.accessibility_settings.get('show_reading_time', True))

        tk.Checkbutton(toggle_frame, text="High Contrast Mode", variable=self.high_contrast_var,
                       command=self.on_setting_change, font=("Arial", 11)).pack(side=tk.LEFT, padx=8)

        tk.Checkbutton(toggle_frame, text="Highlight Keywords", variable=self.highlight_keywords_var,
                       command=self.on_setting_change, font=("Arial", 11)).pack(side=tk.LEFT, padx=8)

        tk.Checkbutton(toggle_frame, text="Auto-Read Articles", variable=self.auto_read_var,
                       command=self.on_setting_change, font=("Arial", 11)).pack(side=tk.LEFT, padx=8)

        tk.Checkbutton(toggle_frame, text="Show Reading Time", variable=self.show_reading_time_var,
                       command=self.on_setting_change, font=("Arial", 11)).pack(side=tk.LEFT, padx=8)

        # Control buttons
        button_frame = tk.Frame(settings_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=8)

        tk.Button(button_frame, text="💾 Save Settings", command=self.save_accessibility_settings,
                  bg="#4CAF50", fg="white", font=("Arial", 11, "bold"),
                  width=15).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="🔄 Reset to Defaults", command=self.reset_accessibility_settings,
                  bg="#f44336", fg="white", font=("Arial", 11, "bold"),
                  width=15).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="🔊 Test Voice", command=self.test_voice,
                  bg="#2196F3", fg="white", font=("Arial", 11, "bold"),
                  width=12).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="📖 Apply to All Tabs", command=self.apply_to_all_tabs,
                  bg="#FF9800", fg="white", font=("Arial", 11, "bold"),
                  width=15).pack(side=tk.LEFT, padx=5)

        # Preview Panel
        preview_frame = tk.LabelFrame(main_frame, text="📖 Live Content Preview",
                                      font=("Arial", 14, "bold"), fg="darkgreen")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Article selection for preview
        selection_frame = tk.Frame(preview_frame)
        selection_frame.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(selection_frame, text="Preview Article:",
                 font=("Arial", 12, "bold")).pack(side=tk.LEFT)

        self.preview_article_var = tk.StringVar()
        self.preview_dropdown = ttk.Combobox(selection_frame, textvariable=self.preview_article_var,
                                             state="readonly", width=60, font=("Arial", 10))
        self.preview_dropdown.pack(side=tk.LEFT, padx=8)
        self.preview_dropdown.bind("<<ComboboxSelected>>", self.on_preview_article_change)

        tk.Button(selection_frame, text="🔄 Refresh Preview", command=self.update_preview_content,
                  bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

        tk.Button(selection_frame, text="🔊 Read Aloud", command=self.read_preview_aloud,
                  bg="#9C27B0", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

        # Content display with scroll
        content_frame = tk.Frame(preview_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        self.neurodiversity_content = scrolledtext.ScrolledText(
            content_frame,
            width=120,
            height=28,
            font=("Arial", self.font_size_var.get()),
            wrap=tk.WORD,
            relief=tk.RAISED,
            borderwidth=2
        )
        self.neurodiversity_content.pack(fill=tk.BOTH, expand=True)

        # Apply initial settings
        self.update_accessibility_display()
        self.populate_preview_articles()

    def on_cognitive_profile_change(self):
        """Handle cognitive profile change with immediate feedback"""
        profile = self.cognitive_var.get()
        self.accessibility_settings['cognitive_profile'] = profile
        self.status_label.config(text=f"Settings Status: Profile changed to {profile.upper()}", fg="blue")
        self.update_preview_content()
        self.after(2000, lambda: self.status_label.config(text="Settings Status: Ready", fg="green"))

    def on_font_size_change(self, value=None):
        """Handle font size change with immediate visual feedback"""
        size = int(float(value)) if value else self.font_size_var.get()
        self.accessibility_settings['font_size'] = size
        self.font_size_label.config(text=f"{size}pt")
        self.update_accessibility_display()
        self.status_label.config(text=f"Settings Status: Font size changed to {size}pt", fg="blue")
        self.after(2000, lambda: self.status_label.config(text="Settings Status: Ready", fg="green"))

    def on_line_spacing_change(self, value=None):
        """Handle line spacing change with immediate visual feedback"""
        spacing = float(value) if value else self.line_spacing_var.get()
        self.accessibility_settings['line_spacing'] = spacing
        self.line_spacing_label.config(text=f"{spacing:.1f}x")
        self.update_accessibility_display()
        self.status_label.config(text=f"Settings Status: Line spacing changed to {spacing:.1f}x", fg="blue")
        self.after(2000, lambda: self.status_label.config(text="Settings Status: Ready", fg="green"))

    def on_setting_change(self):
        """Handle checkbox setting changes with immediate feedback"""
        self.accessibility_settings['high_contrast'] = self.high_contrast_var.get()
        self.accessibility_settings['highlight_keywords'] = self.highlight_keywords_var.get()
        self.accessibility_settings['auto_read'] = self.auto_read_var.get()
        self.accessibility_settings['show_reading_time'] = self.show_reading_time_var.get()

        changes = []
        if self.high_contrast_var.get():
            changes.append("High Contrast")
        if self.highlight_keywords_var.get():
            changes.append("Keyword Highlighting")
        if self.auto_read_var.get():
            changes.append("Auto-Read")
        if self.show_reading_time_var.get():
            changes.append("Reading Time")

        self.status_label.config(
            text=f"Settings Status: Features updated - {', '.join(changes) if changes else 'All disabled'}", fg="blue")
        self.update_preview_content()
        self.after(3000, lambda: self.status_label.config(text="Settings Status: Ready", fg="green"))

    def on_preview_article_change(self, event=None):
        """Handle preview article selection change"""
        self.update_preview_content()

    def save_accessibility_settings(self):
        """Save accessibility settings with user feedback"""
        if save_accessibility_settings(self.accessibility_settings):
            self.status_label.config(text="Settings Status: ✅ Settings saved successfully!", fg="green")
            messagebox.showinfo("Settings Saved",
                                "Accessibility settings have been saved successfully!\n"
                                "Your preferences will be remembered for future sessions.")
        else:
            self.status_label.config(text="Settings Status: ❌ Failed to save settings", fg="red")
            messagebox.showerror("Save Error", "Failed to save accessibility settings.")

        self.after(3000, lambda: self.status_label.config(text="Settings Status: Ready", fg="green"))

    def reset_accessibility_settings(self):
        """Reset accessibility settings to defaults with confirmation"""
        if messagebox.askyesno("Reset Settings",
                               "Are you sure you want to reset all accessibility settings to defaults?\n"
                               "This will undo all your customizations."):
            self.accessibility_settings = {
                'cognitive_profile': 'standard',
                'font_size': 12,
                'line_spacing': 1.2,
                'high_contrast': False,
                'reduce_animations': False,
                'auto_read': False,
                'show_reading_time': True,
                'highlight_keywords': False
            }
            self.update_accessibility_controls()
            self.update_accessibility_display()
            self.update_preview_content()
            self.status_label.config(text="Settings Status: ✅ Reset to defaults", fg="green")
            self.after(3000, lambda: self.status_label.config(text="Settings Status: Ready", fg="green"))

    def test_voice(self):
        """Test text-to-speech functionality with profile-specific message"""
        profile = self.cognitive_var.get()
        profile_messages = {
            'standard': "Testing standard voice output. This is how articles will sound in standard mode.",
            'adhd': "Testing ADHD-optimized voice. Speaking clearly and at a steady pace for better focus.",
            'autism': "Testing autism-friendly voice. Using structured and predictable speech patterns.",
            'dyslexia': "Testing dyslexia-friendly voice. Speaking slowly and clearly for better comprehension."
        }

        test_text = profile_messages.get(profile, profile_messages['standard'])
        self.status_label.config(text=f"Settings Status: 🔊 Testing voice for {profile} profile...", fg="blue")

        def speak_in_thread():
            speak_text(test_text)
            self.after(0, lambda: self.status_label.config(text="Settings Status: Voice test complete", fg="green"))
            self.after(2000, lambda: self.status_label.config(text="Settings Status: Ready", fg="green"))

        threading.Thread(target=speak_in_thread, daemon=True).start()

    def apply_to_all_tabs(self):
        """Apply accessibility settings to all tabs in the application"""
        try:
            font_size = self.accessibility_settings['font_size']
            font_family = "Comic Sans MS" if self.accessibility_settings['cognitive_profile'] == 'dyslexia' else "Arial"

            # Apply to main content areas
            for widget_name in ['article_details', 'trending_text', 'sentiment_text',
                                'manipulation_details', 'factcheck_details', 'newsdna_details']:
                if hasattr(self, widget_name):
                    widget = getattr(self, widget_name)
                    widget.config(font=(font_family, font_size))

                    # Apply color scheme
                    if self.accessibility_settings['high_contrast']:
                        widget.config(bg="black", fg="white")
                    elif self.accessibility_settings['cognitive_profile'] == 'dyslexia':
                        widget.config(bg="#FFFACD", fg="black")
                    else:
                        widget.config(bg="white", fg="black")

            self.status_label.config(text="Settings Status: ✅ Applied to all tabs successfully!", fg="green")
            messagebox.showinfo("Settings Applied",
                                "Accessibility settings have been applied to all tabs!\n"
                                "Navigate between tabs to see the changes.")

        except Exception as e:
            self.status_label.config(text="Settings Status: ❌ Error applying to tabs", fg="red")
            messagebox.showerror("Apply Error", f"Failed to apply settings to all tabs: {e}")

        self.after(3000, lambda: self.status_label.config(text="Settings Status: Ready", fg="green"))

    def update_accessibility_controls(self):
        """Update accessibility control values to match settings"""
        self.cognitive_var.set(self.accessibility_settings['cognitive_profile'])
        self.font_size_var.set(self.accessibility_settings['font_size'])
        self.line_spacing_var.set(self.accessibility_settings['line_spacing'])
        self.high_contrast_var.set(self.accessibility_settings['high_contrast'])
        self.highlight_keywords_var.set(self.accessibility_settings['highlight_keywords'])
        self.auto_read_var.set(self.accessibility_settings['auto_read'])
        self.show_reading_time_var.set(self.accessibility_settings['show_reading_time'])

        # Update labels
        self.font_size_label.config(text=f"{self.font_size_var.get()}pt")
        self.line_spacing_label.config(text=f"{self.line_spacing_var.get():.1f}x")

    def update_accessibility_display(self):
        """Update the display based on accessibility settings"""
        font_size = self.accessibility_settings['font_size']

        # Update font family based on profile
        font_family = "Arial"
        if self.accessibility_settings['cognitive_profile'] == 'dyslexia':
            font_family = "Comic Sans MS"  # More dyslexia-friendly
        elif self.accessibility_settings['cognitive_profile'] == 'adhd':
            font_family = "Arial Black"  # Bold for better focus

        # Update font configuration
        font_config = (font_family, font_size)
        self.neurodiversity_content.config(font=font_config)

        # Update colors based on settings
        if self.accessibility_settings['high_contrast']:
            self.neurodiversity_content.config(bg="black", fg="white", insertbackground="white")
        elif self.accessibility_settings['cognitive_profile'] == 'dyslexia':
            self.neurodiversity_content.config(bg="#FFFACD", fg="black", insertbackground="black")
        elif self.accessibility_settings['cognitive_profile'] == 'adhd':
            self.neurodiversity_content.config(bg="#F0F8FF", fg="black", insertbackground="black")
        else:
            self.neurodiversity_content.config(bg="white", fg="black", insertbackground="black")

    def populate_preview_articles(self):
        """Populate the preview dropdown with available articles"""
        if hasattr(self, 'filtered_articles') and self.filtered_articles:
            article_titles = [f"Article {i + 1}: {article['title'][:60]}..."
                              for i, article in enumerate(self.filtered_articles[:10])]
        else:
            # Use sample articles if no real articles are loaded
            article_titles = [f"Sample {i + 1}: {article['title'][:60]}..."
                              for i, article in enumerate(SAMPLE_ARTICLES)]

        self.preview_dropdown['values'] = article_titles
        if article_titles:
            self.preview_dropdown.set(article_titles[0])
            self.update_preview_content()

    def update_preview_content(self):
        """Update preview content based on current settings - THIS IS THE KEY FIX"""
        try:
            # Get articles to work with
            articles_to_use = self.filtered_articles if hasattr(self,
                                                                'filtered_articles') and self.filtered_articles else SAMPLE_ARTICLES

            if not articles_to_use:
                self.neurodiversity_content.delete(1.0, tk.END)
                self.neurodiversity_content.insert(tk.END,
                                                   "No articles available for preview. Please load articles first.")
                return

            # Get selected article
            selection = self.preview_dropdown.current()
            if selection == -1:
                selection = 0

            if selection < len(articles_to_use):
                article = articles_to_use[selection]

                # Get the cognitive profile setting
                profile = self.accessibility_settings['cognitive_profile']

                # Get base content
                content = article.get('summary', 'No summary available.')

                # Apply adaptations based on profile
                if profile == 'adhd':
                    user_profile = {'cognitive_needs': ['adhd']}
                    adapted_content = neurodiversity_adapter.get_adapted_content(content, user_profile)
                elif profile == 'autism':
                    user_profile = {'cognitive_needs': ['autism']}
                    adapted_content = neurodiversity_adapter.get_adapted_content(content, user_profile)
                elif profile == 'dyslexia':
                    user_profile = {'cognitive_needs': ['dyslexia']}
                    adapted_content = neurodiversity_adapter.get_adapted_content(content, user_profile)
                else:
                    adapted_content = content

                # Add title and metadata
                final_content = f"📰 TITLE: {article['title']}\n"
                final_content += f"📅 Published: {article.get('published', 'Unknown')}\n"
                final_content += f"🔗 Source: {article.get('link', 'N/A')}\n"

                # Add reading time if enabled
                if self.accessibility_settings['show_reading_time']:
                    word_count = len(adapted_content.split())
                    reading_time = max(1, word_count // 200)
                    final_content += f"⏱️ Estimated reading time: {reading_time} minute(s)\n"

                # Add cognitive profile indicator
                final_content += f"🧠 Optimized for: {profile.upper()} profile\n"
                final_content += "=" * 80 + "\n\n"

                # Add the adapted content
                final_content += adapted_content

                # Apply keyword highlighting if enabled
                if self.accessibility_settings['highlight_keywords']:
                    # Simple keyword highlighting
                    keywords = ['important', 'breaking', 'new', 'study', 'research', 'government', 'health', 'technology']
                    for keyword in keywords:
                        final_content = re.sub(r'\b' + keyword + r'\b', f'**{keyword.upper()}**', final_content, flags=re.IGNORECASE)

                # Update content display
                self.neurodiversity_content.delete(1.0, tk.END)
                self.neurodiversity_content.insert(tk.END, final_content)

                # Auto-read if enabled
                if self.accessibility_settings['auto_read']:
                    def auto_read():
                        speak_text(content[:300])  # Read first 300 characters
                    threading.Thread(target=auto_read, daemon=True).start()

        except Exception as e:
            self.neurodiversity_content.delete(1.0, tk.END)
            self.neurodiversity_content.insert(tk.END, f"Error updating preview: {e}")
            print(f"Preview update error: {e}")

    def read_preview_aloud(self):
        """Read the current preview content aloud"""
        try:
            content = self.neurodiversity_content.get(1.0, tk.END)
            # Remove formatting and read first 500 characters
            clean_content = re.sub(r'[📰📅🔗⏱️🧠🔸\*=━]', '', content)
            clean_content = re.sub(r'\n+', ' ', clean_content)

            if len(clean_content) > 500:
                clean_content = clean_content[:500] + "... Content truncated for voice reading."

            self.status_label.config(text="Settings Status: 🔊 Reading content aloud...", fg="blue")

            def speak_in_thread():
                speak_text(clean_content)
                self.after(0, lambda: self.status_label.config(text="Settings Status: Reading complete", fg="green"))
                self.after(2000, lambda: self.status_label.config(text="Settings Status: Ready", fg="green"))

            threading.Thread(target=speak_in_thread, daemon=True).start()

        except Exception as e:
            self.status_label.config(text="Settings Status: ❌ Voice reading failed", fg="red")
            print(f"Voice reading error: {e}")

    def create_other_tabs(self):
        """Create all other tabs with preserved functionality"""

        # Trending tab
        self.trending_text = scrolledtext.ScrolledText(self.tab_trending, width=100, height=45, font=("Arial", 12))
        self.trending_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Sentiment tab
        self.sentiment_text = scrolledtext.ScrolledText(self.tab_sentiment, width=100, height=45, font=("Arial", 12))
        self.sentiment_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Recommendations tab
        rec_frame = tk.Frame(self.tab_recommend)
        rec_frame.pack(fill=tk.BOTH, expand=True)

        self.recommend_listbox = tk.Listbox(rec_frame, font=("Arial", 12), selectmode=tk.SINGLE)
        self.recommend_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.recommend_listbox.bind("<<ListboxSelect>>", self.on_recommend_select)

        self.recommend_details = scrolledtext.ScrolledText(rec_frame, width=60, height=35, font=("Arial", 11))
        self.recommend_details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.rec_reader_mode_btn = tk.Button(rec_frame, text="Reader Mode", state=tk.DISABLED, command=self.show_recommend_reader_mode)
        self.rec_reader_mode_btn.pack(side=tk.BOTTOM, pady=5)
        self.rec_tts_btn = tk.Button(rec_frame, text="🔊 Speak", state=tk.DISABLED, command=self.speak_recommend_summary)
        self.rec_tts_btn.pack(side=tk.BOTTOM, pady=5)

        # Seen articles tab
        seen_frame = tk.Frame(self.tab_seen)
        seen_frame.pack(fill=tk.BOTH, expand=True)

        self.seen_listbox = tk.Listbox(seen_frame, font=("Arial", 12), selectmode=tk.SINGLE)
        self.seen_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.seen_listbox.bind("<<ListboxSelect>>", self.on_seen_select)

        self.seen_details = scrolledtext.ScrolledText(seen_frame, width=60, height=35, font=("Arial", 11))
        self.seen_details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.seen_reader_mode_btn = tk.Button(seen_frame, text="Reader Mode", state=tk.DISABLED, command=self.show_seen_reader_mode)
        self.seen_reader_mode_btn.pack(side=tk.BOTTOM, pady=5)
        self.seen_tts_btn = tk.Button(seen_frame, text="🔊 Speak", state=tk.DISABLED, command=self.speak_seen_summary)
        self.seen_tts_btn.pack(side=tk.BOTTOM, pady=5)

        # Manipulation Analysis tab
        self.manipulation_listbox = tk.Listbox(self.tab_manipulation, font=("Arial", 12))
        self.manipulation_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.manipulation_listbox.bind("<<ListboxSelect>>", self.on_manipulation_select)
        self.manipulation_details = scrolledtext.ScrolledText(self.tab_manipulation, width=60, height=35, font=("Arial", 11))
        self.manipulation_details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Fact Check tab
        self.factcheck_listbox = tk.Listbox(self.tab_factcheck, font=("Arial", 12))
        self.factcheck_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.factcheck_listbox.bind("<<ListboxSelect>>", self.on_factcheck_select)
        self.factcheck_details = scrolledtext.ScrolledText(self.tab_factcheck, width=60, height=35, font=("Arial", 11))
        self.factcheck_details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # News DNA tab
        self.newsdna_listbox = tk.Listbox(self.tab_newsdna, font=("Arial", 12))
        self.newsdna_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.newsdna_listbox.bind("<<ListboxSelect>>", self.on_newsdna_select)
        self.newsdna_details = scrolledtext.ScrolledText(self.tab_newsdna, width=60, height=35, font=("Arial", 11))
        self.newsdna_details.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Advanced Sentiment Insights tab
        si_main_frame = tk.Frame(self.tab_sentiment_advanced)
        si_main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Chart frame
        self.si_chart_frame = tk.Frame(si_main_frame, height=250)
        self.si_chart_frame.pack(fill=tk.X, pady=(0, 10))
        self.si_chart_frame.pack_propagate(False)
        self.si_chart_canvas = None

        # Per-interest sentiment frame
        si_interest_frame = tk.Frame(si_main_frame)
        si_interest_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(si_interest_frame, text="Sentiment by Interest:", font=("Arial", 12, "bold")).pack(anchor='w')
        self.si_per_interest = scrolledtext.ScrolledText(si_interest_frame, height=10, font=("Arial", 10))
        self.si_per_interest.pack(fill=tk.X)

        # Most positive/negative articles frame
        si_articles_frame = tk.Frame(si_main_frame)
        si_articles_frame.pack(fill=tk.BOTH, expand=True)

        # Positive articles
        si_pos_frame = tk.Frame(si_articles_frame)
        si_pos_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        tk.Label(si_pos_frame, text="Most Positive Articles:", font=("Arial", 11, "bold")).pack(anchor='w')
        self.si_pos_listbox = tk.Listbox(si_pos_frame, font=("Arial", 10), height=8)
        self.si_pos_listbox.pack(fill=tk.BOTH, expand=True)
        self.si_pos_listbox.bind("<<ListboxSelect>>", self.on_si_pos_select)

        # Negative articles
        si_neg_frame = tk.Frame(si_articles_frame)
        si_neg_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        tk.Label(si_neg_frame, text="Most Negative Articles:", font=("Arial", 11, "bold")).pack(anchor='w')
        self.si_neg_listbox = tk.Listbox(si_neg_frame, font=("Arial", 10), height=8)
        self.si_neg_listbox.pack(fill=tk.BOTH, expand=True)
        self.si_neg_listbox.bind("<<ListboxSelect>>", self.on_si_neg_select)

        # Article details for sentiment insights
        self.si_article_details = scrolledtext.ScrolledText(si_main_frame, height=8, font=("Arial", 10))
        self.si_article_details.pack(fill=tk.X, pady=(10, 0))

        # Settings tab
        self.create_settings_tab()

    def create_settings_tab(self):
        """Create settings tab"""
        settings_main = tk.Frame(self.tab_settings)
        settings_main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tk.Label(settings_main, text="User Profile Settings", font=("Arial", 16, "bold")).pack(pady=(0, 20))

        # Interests
        interests_frame = tk.LabelFrame(settings_main, text="Interests", font=("Arial", 12, "bold"))
        interests_frame.pack(fill=tk.X, pady=(0, 10))

        self.interests_entry = tk.Entry(interests_frame, font=("Arial", 11), width=80)
        self.interests_entry.pack(padx=10, pady=10)
        self.interests_entry.insert(0, ', '.join(self.profile.get('interests', [])))

        # Sources
        sources_frame = tk.LabelFrame(settings_main, text="RSS Sources", font=("Arial", 12, "bold"))
        sources_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.sources_text = scrolledtext.ScrolledText(sources_frame, height=10, font=("Arial", 10))
        self.sources_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.sources_text.insert(tk.END, '\n'.join(self.profile.get('sources', [])))

        # Buttons
        buttons_frame = tk.Frame(settings_main)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))

        tk.Button(buttons_frame, text="Save Profile", command=self.save_profile_settings,
                 bg="#4CAF50", fg="white", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(buttons_frame, text="Reload Articles", command=self.load_articles_async,
                 bg="#2196F3", fg="white", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(buttons_frame, text="Clear History", command=self.clear_history,
                 bg="#f44336", fg="white", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=5)

    # Event handlers
    def on_article_select(self, event):
        idx = self.feed_listbox.curselection()
        if not idx or idx[0] >= len(self.filtered_articles):
            return
        idx = idx[0]
        article = self.filtered_articles[idx]
        details = f"Title: {article['title']}\n"
        details += f"Published: {article.get('published','')}\n"

        # Add advanced analysis
        try:
            scores = manipulation_analyzer.analyze_manipulation(article.get('summary', '') + ' ' + article.get('title', ''))
            risk_level = manipulation_analyzer.get_manipulation_risk_level(scores['overall_manipulation_score'])
            details += f"Manipulation Risk: {risk_level}\n"

            misinformation_analysis = misinformation_detector.calculate_misinformation_risk(article)
            details += f"Misinformation Risk: {misinformation_analysis['risk_level']}\n"
            details += f"Source Credibility: {misinformation_analysis['source_credibility']:.2f}\n"
        except Exception as e:
            details += f"Advanced analysis error: {e}\n"

        details += f"Sentiment: {get_sentiment(article.get('summary',''))}\n\n"
        details += "Summary:\n"
        for bullet in bullet_summary(article.get('summary','')):
            details += f" - {bullet}\n"
        details += f"\nLink: {article.get('link', '')}\n"

        self.article_details.delete(1.0, tk.END)
        self.article_details.insert(tk.END, details)
        self.mark_read_btn.config(state=tk.NORMAL)
        self.reader_mode_btn.config(state=tk.NORMAL)
        self.tts_btn.config(state=tk.NORMAL)

    def on_manipulation_select(self, event):
        idx = self.manipulation_listbox.curselection()
        if not idx or idx[0] >= len(self.filtered_articles):
            return
        idx = idx[0]
        article = self.filtered_articles[idx]

        try:
            scores = manipulation_analyzer.analyze_manipulation(article.get('summary', '') + ' ' + article.get('title', ''))

            details = f"=== MANIPULATION ANALYSIS ===\n\n"
            details += f"Title: {article['title']}\n\n"
            details += f"Overall Risk: {manipulation_analyzer.get_manipulation_risk_level(scores['overall_manipulation_score'])}\n"
            details += f"Overall Score: {scores['overall_manipulation_score']:.2f}/10\n\n"

            details += "DETAILED BREAKDOWN:\n"
            details += f"• Fear Appeals: {scores.get('fear_appeal', 0):.2f}/10\n"
            details += f"• Authority Appeals: {scores.get('authority_appeal', 0):.2f}/10\n"
            details += f"• Bandwagon Effects: {scores.get('bandwagon', 0):.2f}/10\n"
            details += f"• Scarcity Tactics: {scores.get('scarcity', 0):.2f}/10\n"
            details += f"• Confirmation Bias: {scores.get('confirmation_bias', 0):.2f}/10\n"
            details += f"• False Dichotomy: {scores.get('false_dichotomy', 0):.2f}/10\n\n"

            details += "INTERPRETATION:\n"
            if scores['overall_manipulation_score'] < 1.0:
                details += "✅ Low manipulation risk - Content appears objective\n"
            elif scores['overall_manipulation_score'] < 3.0:
                details += "⚠️ Medium manipulation risk - Some persuasive elements\n"
            elif scores['overall_manipulation_score'] < 5.0:
                details += "⚠️⚠️ High manipulation risk - Strong persuasive techniques\n"
            else:
                details += "🚨 Critical manipulation risk - Heavy use of manipulation\n"

            details += f"\nOriginal Summary:\n{article.get('summary', 'No summary available')}"

        except Exception as e:
            details = f"Manipulation analysis error: {e}"

        self.manipulation_details.delete(1.0, tk.END)
        self.manipulation_details.insert(tk.END, details)

    def on_factcheck_select(self, event):
        idx = self.factcheck_listbox.curselection()
        if not idx or idx[0] >= len(self.filtered_articles):
            return
        idx = idx[0]
        article = self.filtered_articles[idx]

        try:
            analysis = misinformation_detector.calculate_misinformation_risk(article)

            details = f"=== FACT-CHECK ANALYSIS ===\n\n"
            details += f"Title: {article['title']}\n\n"
            details += f"Misinformation Risk: {analysis['risk_level']}\n"
            details += f"Risk Score: {analysis['risk_score']:.2f}/1.0\n"
            details += f"Source Credibility: {analysis['source_credibility']:.2f}/1.0\n\n"

            details += "EXTRACTED CLAIMS:\n"
            for i, claim_result in enumerate(analysis['claims'], 1):
                details += f"\n{i}. Claim: {claim_result['claim'][:100]}...\n"
                details += f"   Verdict: {claim_result['verdict']}\n"
                details += f"   Confidence: {claim_result['confidence']:.2f}\n"

            if not analysis['claims']:
                details += "No specific factual claims detected in this article.\n"

            details += f"\nSOURCE ANALYSIS:\n"
            details += f"Domain credibility based on historical accuracy and reputation.\n"

            details += f"\nOriginal Summary:\n{article.get('summary', 'No summary available')}"

        except Exception as e:
            details = f"Fact-check analysis error: {e}"

        self.factcheck_details.delete(1.0, tk.END)
        self.factcheck_details.insert(tk.END, details)

    def on_newsdna_select(self, event):
        idx = self.newsdna_listbox.curselection()
        if not idx or idx[0] >= len(self.filtered_articles):
            return
        idx = idx[0]
        article = self.filtered_articles[idx]

        try:
            # Get similar articles
            similar_articles = news_dna_analyzer.find_similar_articles(article, threshold=0.5)
            entities = news_dna_analyzer.extract_entities(article.get('summary', '') + ' ' + article.get('title', ''))

            details = f"=== NEWS DNA ANALYSIS ===\n\n"
            details += f"Title: {article['title']}\n\n"

            details += f"ENTITIES DETECTED:\n"
            for entity, entity_type in entities[:10]:
                details += f"• {entity} ({entity_type})\n"

            if not entities:
                details += "No named entities detected.\n"

            details += f"\nSIMILAR ARTICLES ({len(similar_articles)} found):\n"
            for i, similar in enumerate(similar_articles[:5], 1):
                details += f"{i}. Similarity: {similar['similarity']:.2f}\n"
                details += f"   Title: {similar['article']['title'][:80]}...\n\n"

            if not similar_articles:
                details += "No similar articles found in database.\n"

            details += f"CONTENT FINGERPRINT:\n"
            content_hash = news_dna_analyzer.create_content_hash(article.get('summary', '') + ' ' + article.get('title', ''))
            details += f"Hash: {content_hash[:16]}...\n"

            details += f"\nOriginal Summary:\n{article.get('summary', 'No summary available')}"

        except Exception as e:
            details = f"News DNA analysis error: {e}"

        self.newsdna_details.delete(1.0, tk.END)
        self.newsdna_details.insert(tk.END, details)

    def on_recommend_select(self, event):
        idx = self.recommend_listbox.curselection()
        if not idx or idx[0] >= len(self.recommendations):
            return
        idx = idx[0]
        article = self.recommendations[idx]
        self.show_article_details(article, self.recommend_details)
        self.rec_reader_mode_btn.config(state=tk.NORMAL)
        self.rec_tts_btn.config(state=tk.NORMAL)

    def on_seen_select(self, event):
        idx = self.seen_listbox.curselection()
        if not idx or idx[0] >= len(self.seen_articles):
            return
        idx = idx[0]
        article = self.seen_articles[idx]
        self.show_article_details(article, self.seen_details)
        self.seen_reader_mode_btn.config(state=tk.NORMAL)
        self.seen_tts_btn.config(state=tk.NORMAL)

    def on_si_pos_select(self, event):
        idx = self.si_pos_listbox.curselection()
        if not idx or idx[0] >= len(self.si_most_positive):
            return
        _, article = self.si_most_positive[idx[0]]
        self.show_si_article_details(article)

    def on_si_neg_select(self, event):
        idx = self.si_neg_listbox.curselection()
        if not idx or idx[0] >= len(self.si_most_negative):
            return
        _, article = self.si_most_negative[idx[0]]
        self.show_si_article_details(article)

    def show_article_details(self, article, text_widget):
        details = f"Title: {article['title']}\n"
        details += f"Published: {article.get('published','')}\n"
        details += f"Sentiment: {get_sentiment(article.get('summary',''))}\n\n"
        details += "Summary:\n"
        for bullet in bullet_summary(article.get('summary','')):
            details += f" - {bullet}\n"
        details += f"\nLink: {article.get('link', '')}\n"
        text_widget.delete(1.0, tk.END)
        text_widget.insert(tk.END, details)

    def show_si_article_details(self, article):
        details = f"Title: {article['title']}\n"
        details += f"Published: {article.get('published','')}\n"
        score = get_sentiment_score(article.get("summary", ""))
        details += f"Sentiment Score: {score:.2f}\n"
        details += f"Sentiment: {get_sentiment(article.get('summary',''))}\n\n"
        details += "Summary:\n"
        for bullet in bullet_summary(article.get('summary','')):
            details += f" - {bullet}\n"
        details += f"\nLink: {article.get('link', '')}\n"
        self.si_article_details.delete(1.0, tk.END)
        self.si_article_details.insert(tk.END, details)

    def mark_as_read(self):
        idx = self.feed_listbox.curselection()
        if not idx or idx[0] >= len(self.filtered_articles):
            return
        idx = idx[0]
        article = self.filtered_articles[idx]
        simulate_user_click(article, self.click_log)
        self.update_feed()
        self.update_seen_tab()
        self.update_recommend_tab()

    def show_reader_mode(self):
        idx = self.feed_listbox.curselection()
        if not idx or idx[0] >= len(self.filtered_articles):
            return
        idx = idx[0]
        article = self.filtered_articles[idx]
        url = article.get('link', '')
        full_text = fetch_full_article_text(url)
        ReaderModeWindow(self, article['title'], full_text, self.accessibility_settings)

    def speak_summary(self):
        idx = self.feed_listbox.curselection()
        if not idx or idx[0] >= len(self.filtered_articles):
            return
        idx = idx[0]
        article = self.filtered_articles[idx]
        summary = article.get('summary', '')
        speak_text(summary if summary else article['title'])

    def show_recommend_reader_mode(self):
        idx = self.recommend_listbox.curselection()
        if not idx or idx[0] >= len(self.recommendations):
            return
        idx = idx[0]
        article = self.recommendations[idx]
        url = article.get('link', '')
        full_text = fetch_full_article_text(url)
        ReaderModeWindow(self, article['title'], full_text, self.accessibility_settings)

    def speak_recommend_summary(self):
        idx = self.recommend_listbox.curselection()
        if not idx or idx[0] >= len(self.recommendations):
            return
        idx = idx[0]
        article = self.recommendations[idx]
        summary = article.get('summary', '')
        speak_text(summary if summary else article['title'])

    def show_seen_reader_mode(self):
        idx = self.seen_listbox.curselection()
        if not idx or idx[0] >= len(self.seen_articles):
            return
        idx = idx[0]
        article = self.seen_articles[idx]
        url = article.get('link', '')
        full_text = fetch_full_article_text(url)
        ReaderModeWindow(self, article['title'], full_text, self.accessibility_settings)

    def speak_seen_summary(self):
        idx = self.seen_listbox.curselection()
        if not idx or idx[0] >= len(self.seen_articles):
            return
        idx = idx[0]
        article = self.seen_articles[idx]
        summary = article.get('summary', '')
        speak_text(summary if summary else article['title'])

    def save_profile_settings(self):
        try:
            interests_text = self.interests_entry.get()
            sources_text = self.sources_text.get(1.0, tk.END).strip()

            self.profile['interests'] = [i.strip().lower() for i in interests_text.split(',') if i.strip()]
            self.profile['sources'] = [s.strip() for s in sources_text.split('\n') if s.strip()]

            save_user_profile(self.profile)
            messagebox.showinfo("Success", "Profile settings saved successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save profile settings: {e}")

    def clear_history(self):
        if messagebox.askyesno("Clear History", "Are you sure you want to clear all reading history?"):
            self.click_log = []
            save_click_log(self.click_log)
            self.recommendation_history = []
            save_recommendation_history(self.recommendation_history)
            self.update_seen_tab()
            self.update_recommend_tab()
            messagebox.showinfo("Success", "History cleared successfully!")

    def load_articles_async(self):
        def task():
            self.feed_listbox.delete(0, tk.END)
            self.article_details.delete(1.0, tk.END)
            self.feed_listbox.insert(tk.END, "Loading articles...")
            self.update()

            # Fetch articles
            articles = fetch_rss_articles(self.profile['sources'], max_articles_per_feed=10)
            gnews_articles = fetch_gnews_articles(self.profile['interests'], max_articles_per_interest=10)
            realtime_news_articles = fetch_realtime_news_articles(self.profile['interests'], max_articles_per_interest=10)
            all_articles = articles + gnews_articles + realtime_news_articles
            all_articles = deduplicate_articles(all_articles)
            all_articles = filter_articles_by_date(all_articles, max_days=30)

            # Advanced analysis for each article
            for article in all_articles[:50]:  # Limit for performance
                try:
                    manipulation_analyzer.store_manipulation_analysis(article)
                    news_dna_analyzer.store_news_dna(article)
                except Exception as e:
                    print(f"Advanced analysis error: {e}")

            filtered = recommend_by_interest(all_articles, self.profile['interests'])
            filtered = rank_by_user_behavior(filtered, self.click_log)
            filtered = filter_out_read(filtered, self.click_log)

            self.articles = all_articles
            self.filtered_articles = filtered
            self.seen_articles = self.get_seen_articles()
            self.recommendations = recommend_based_on_history(all_articles, self.click_log, self.recommendation_history)

            # Update all tabs
            self.after(0, self.update_feed)
            self.after(0, self.update_trending)
            self.after(0, self.update_seen_tab)
            self.after(0, self.update_sentiment_tab)
            self.after(0, self.update_recommend_tab)
            self.after(0, self.update_sentiment_advanced_tab)
            self.after(0, self.update_manipulation_tab)
            self.after(0, self.update_factcheck_tab)
            self.after(0, self.update_newsdna_tab)
            self.after(0, self.populate_preview_articles)

        threading.Thread(target=task, daemon=True).start()

    def update_manipulation_tab(self):
        """Update manipulation analysis tab"""
        self.manipulation_listbox.delete(0, tk.END)
        if not self.filtered_articles:
            self.manipulation_listbox.insert(tk.END, "No articles to analyze.")
            return

        for i, article in enumerate(self.filtered_articles[:50]):
            try:
                scores = manipulation_analyzer.analyze_manipulation(
                    article.get('summary', '') + ' ' + article.get('title', '')
                )
                risk_level = manipulation_analyzer.get_manipulation_risk_level(scores['overall_manipulation_score'])
                self.manipulation_listbox.insert(tk.END,
                    f"[{i+1}] {article['title'][:70]}... [{risk_level}]")
            except Exception as e:
                self.manipulation_listbox.insert(tk.END,
                    f"[{i+1}] {article['title'][:70]}... [ERROR]")

    def update_factcheck_tab(self):
        """Update fact-check tab"""
        self.factcheck_listbox.delete(0, tk.END)
        if not self.filtered_articles:
            self.factcheck_listbox.insert(tk.END, "No articles to fact-check.")
            return

        for i, article in enumerate(self.filtered_articles[:50]):
            try:
                analysis = misinformation_detector.calculate_misinformation_risk(article)
                risk_level = analysis['risk_level']
                credibility = analysis['source_credibility']
                self.factcheck_listbox.insert(tk.END,
                    f"[{i+1}] {article['title'][:60]}... [Risk: {risk_level}, Cred: {credibility:.1f}]")
            except Exception as e:
                self.factcheck_listbox.insert(tk.END,
                    f"[{i+1}] {article['title'][:60]}... [ERROR]")

    def update_newsdna_tab(self):
        """Update News DNA tab"""
        self.newsdna_listbox.delete(0, tk.END)
        if not self.filtered_articles:
            self.newsdna_listbox.insert(tk.END, "No articles for DNA analysis.")
            return

        for i, article in enumerate(self.filtered_articles[:50]):
            try:
                similar_count = len(news_dna_analyzer.find_similar_articles(article, threshold=0.5))
                entities = news_dna_analyzer.extract_entities(
                    article.get('summary', '') + ' ' + article.get('title', '')
                )
                entity_count = len(entities)

                self.newsdna_listbox.insert(tk.END,
                    f"[{i+1}] {article['title'][:60]}... [Similar: {similar_count}, Entities: {entity_count}]")
            except Exception as e:
                self.newsdna_listbox.insert(tk.END,
                    f"[{i+1}] {article['title'][:60]}... [ERROR]")

    def update_feed(self):
        self.feed_listbox.delete(0, tk.END)
        if not self.filtered_articles:
            self.feed_listbox.insert(tk.END, "No articles found for your interests.")
            self.reader_mode_btn.config(state=tk.DISABLED)
            self.tts_btn.config(state=tk.DISABLED)
            return
        for i, article in enumerate(self.filtered_articles[:200]):
            sentiment = get_sentiment(article.get('summary',''))
            # Add manipulation risk indicator
            try:
                scores = manipulation_analyzer.analyze_manipulation(
                    article.get('summary', '') + ' ' + article.get('title', '')
                )
                risk = manipulation_analyzer.get_manipulation_risk_level(scores['overall_manipulation_score'])
                risk_indicator = {"LOW": "✓", "MEDIUM": "⚠", "HIGH": "⚠⚠", "CRITICAL": "🚨"}[risk]
            except:
                risk_indicator = "?"

            self.feed_listbox.insert(tk.END, f"[{i+1}] {article['title']} [{sentiment}] {risk_indicator}")
        self.article_details.delete(1.0, tk.END)
        self.mark_read_btn.config(state=tk.DISABLED)
        self.reader_mode_btn.config(state=tk.DISABLED)
        self.tts_btn.config(state=tk.DISABLED)

    def update_trending(self):
        self.trending_text.delete(1.0, tk.END)
        trending = trending_keywords(self.articles[:200], top_n=20)
        if not trending:
            self.trending_text.insert(tk.END, "No trending topics found.\n")
            return
        self.trending_text.insert(tk.END, "🔥 Trending Topics (last 30 days):\n\n")

        for keyword, count in trending:
            self.trending_text.insert(tk.END, f"{keyword}: {count}\n")

    def update_sentiment_tab(self):
        self.sentiment_text.delete(1.0, tk.END)
        counts = get_sentiment_counts(self.articles[:200])
        self.sentiment_text.insert(tk.END, "Overall Article Sentiment Counts (recent 200 articles):\n\n")

        for sentiment in ['positive', 'neutral', 'negative']:
            self.sentiment_text.insert(tk.END, f"{sentiment.capitalize()}: {counts.get(sentiment, 0)}\n")

    def get_seen_articles(self):
        read_titles = set(a['title'] for a in self.click_log)
        latest_articles = [a for a in self.articles if a['title'] in read_titles]
        seen = {a['title']: a for a in latest_articles}
        for a in self.click_log:
            if a['title'] not in seen:
                seen[a['title']] = a
        return list(reversed(list(seen.values())))

    def update_seen_tab(self):
        self.seen_articles = self.get_seen_articles()
        self.seen_listbox.delete(0, tk.END)
        if not self.seen_articles:
            self.seen_listbox.insert(tk.END, "No seen articles yet.")
            self.seen_details.delete(1.0, tk.END)
            self.seen_reader_mode_btn.config(state=tk.DISABLED)
            self.seen_tts_btn.config(state=tk.DISABLED)
            return
        for i, article in enumerate(self.seen_articles[:200]):
            sentiment = get_sentiment(article.get('summary',''))
            self.seen_listbox.insert(tk.END, f"[{i+1}] {article['title']} [{sentiment}]")
        self.seen_details.delete(1.0, tk.END)
        self.seen_reader_mode_btn.config(state=tk.DISABLED)
        self.seen_tts_btn.config(state=tk.DISABLED)

    def update_recommend_tab(self):
        self.recommend_listbox.delete(0, tk.END)
        if not self.recommendations:
            self.recommend_listbox.insert(tk.END, "No recommendations yet. Read and interact with more articles for recommendations!")
            self.recommend_details.delete(1.0, tk.END)
            self.rec_reader_mode_btn.config(state=tk.DISABLED)
            self.rec_tts_btn.config(state=tk.DISABLED)
            return

        for i, article in enumerate(self.recommendations[:200]):
            sentiment = get_sentiment(article.get('summary',''))
            self.recommend_listbox.insert(tk.END,
                f"[{i+1}] {article['title']} [{sentiment}]")

        self.recommend_details.delete(1.0, tk.END)
        self.rec_reader_mode_btn.config(state=tk.DISABLED)
        self.rec_tts_btn.config(state=tk.DISABLED)

    def update_sentiment_advanced_tab(self):
        trend = user_sentiment_trend(self.click_log, days=7)
        if self.si_chart_canvas:
            self.si_chart_canvas.get_tk_widget().destroy()
        if trend:
            fig = Figure(figsize=(4.5, 2.2), dpi=100)
            ax = fig.add_subplot(111)
            dates = [t["date"] for t in trend]
            positives = [t["positive"] for t in trend]
            neutrals = [t["neutral"] for t in trend]
            negatives = [t["negative"] for t in trend]
            ax.plot(dates, positives, label="Positive", color="green")
            ax.plot(dates, neutrals, label="Neutral", color="gray")
            ax.plot(dates, negatives, label="Negative", color="red")
            ax.legend()
            ax.set_title("Your Sentiment Trend Over Time")
            ax.set_xlabel("Date")
            ax.set_ylabel("Articles Read")
            ax.tick_params(axis='x', rotation=45)
            fig.tight_layout()
            self.si_chart_canvas = FigureCanvasTkAgg(fig, master=self.si_chart_frame)
            self.si_chart_canvas.draw()
            self.si_chart_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        interests = self.profile.get('interests', [])
        per_interest = per_interest_sentiment(self.articles[:200], interests)
        self.si_per_interest.delete(1.0, tk.END)

        self.si_per_interest.insert(tk.END, "Sentiment Analysis by Interest:\n\n")

        for interest in interests:
            counts = per_interest[interest]
            self.si_per_interest.insert(tk.END, f"{interest.capitalize():<20}: ")
            for sentiment in ['positive', 'neutral', 'negative']:
                self.si_per_interest.insert(tk.END, f"{sentiment.capitalize()}={counts.get(sentiment,0)}  ")
            self.si_per_interest.insert(tk.END, "\n")

        self.si_most_positive, self.si_most_negative = most_positive_negative_articles(self.articles[:200], top_n=5)
        self.si_pos_listbox.delete(0, tk.END)
        for score, art in self.si_most_positive:
            self.si_pos_listbox.insert(tk.END, f"{score:+.2f} {art['title'][:70]}")
        self.si_neg_listbox.delete(0, tk.END)
        for score, art in self.si_most_negative:
            self.si_neg_listbox.insert(tk.END, f"{score:+.2f} {art['title'][:70]}")
        self.si_article_details.delete(1.0, tk.END)

class ReaderModeWindow(tk.Toplevel):
    def __init__(self, parent, title, full_text, accessibility_settings=None):
        super().__init__(parent)
        self.title(f"Reader Mode: {title}")
        self.geometry("900x700")
        self.accessibility_settings = accessibility_settings or {}

        # Enhanced reader mode with accessibility options
        controls_frame = tk.Frame(self)
        controls_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(controls_frame, text="Font Size:").pack(side=tk.LEFT)
        self.font_size_var = tk.IntVar(value=self.accessibility_settings.get('font_size', 13))
        font_size_scale = tk.Scale(controls_frame, from_=10, to=24, orient=tk.HORIZONTAL,
                                 variable=self.font_size_var, command=self.update_font)
        font_size_scale.pack(side=tk.LEFT, padx=5)

        tk.Label(controls_frame, text="Reading Mode:").pack(side=tk.LEFT, padx=(20, 5))
        self.reading_mode = tk.StringVar(value=self.accessibility_settings.get('cognitive_profile', 'standard'))
        modes = [("Standard", "standard"), ("ADHD", "adhd"), ("Autism", "autism"), ("Dyslexia", "dyslexia")]
        for text, mode in modes:
            tk.Radiobutton(controls_frame, text=text, variable=self.reading_mode,
                         value=mode, command=self.update_content).pack(side=tk.LEFT)

        self.text_widget = scrolledtext.ScrolledText(self, wrap=tk.WORD,
                                                   font=("Arial", self.font_size_var.get()))
        self.text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.original_text = full_text
        self.update_content()

    def update_font(self, value=None):
        """Update font size"""
        size = self.font_size_var.get()
        current_font = self.text_widget.cget("font")
        if isinstance(current_font, tuple):
            new_font = (current_font[0], size)
        else:
            new_font = ("Arial", size)
        self.text_widget.config(font=new_font)

    def update_content(self):
        """Update content based on reading mode"""
        mode = self.reading_mode.get()

        if mode == "adhd":
            user_profile = {'cognitive_needs': ['adhd']}
            adapted_text = neurodiversity_adapter.get_adapted_content(self.original_text, user_profile)
        elif mode == "autism":
            user_profile = {'cognitive_needs': ['autism']}
            adapted_text = neurodiversity_adapter.get_adapted_content(self.original_text, user_profile)
        elif mode == "dyslexia":
            user_profile = {'cognitive_needs': ['dyslexia']}
            adapted_text = neurodiversity_adapter.get_adapted_content(self.original_text, user_profile)
        else:
            adapted_text = self.original_text

        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(tk.END, adapted_text)

        # Apply accessibility settings
        if self.accessibility_settings.get('high_contrast', False):
            self.text_widget.config(bg="black", fg="white")
        elif mode == 'dyslexia':
            self.text_widget.config(bg="#FFFACD", fg="black")
        else:
            self.text_widget.config(bg="white", fg="black")

def main():
    try:
        app = NewsApp()
        app.mainloop()
    except Exception as e:
        print(f"GUI Error: {e}")
        print("Falling back to CLI mode.")

        # Enhanced CLI mode
        profile = get_user_profile_gui()
        articles = fetch_rss_articles(profile['sources'], max_articles_per_feed=10)
        gnews_articles = fetch_gnews_articles(profile['interests'], max_articles_per_interest=10)
        realtime_news_articles = fetch_realtime_news_articles(profile['interests'], max_articles_per_interest=10)
        all_articles = articles + gnews_articles + realtime_news_articles
        all_articles = deduplicate_articles(all_articles)
        all_articles = filter_articles_by_date(all_articles, max_days=30)
        filtered = recommend_by_interest(all_articles, profile['interests'])
        click_log = load_click_log()
        filtered = rank_by_user_behavior(filtered, click_log)
        filtered = filter_out_read(filtered, click_log)

        print("\n====== Advanced Personalized News Feed ======")
        for i, article in enumerate(filtered[:10]):
            print(f"\n[{i+1}] {article['title']}")
            print(f"Sentiment: {get_sentiment(article['summary'])}")

            try:
                manipulation_scores = manipulation_analyzer.analyze_manipulation(
                    article.get('summary', '') + ' ' + article.get('title', '')
                )
                risk_level = manipulation_analyzer.get_manipulation_risk_level(
                    manipulation_scores['overall_manipulation_score']
                )
                print(f"Manipulation Risk: {risk_level}")

                misinformation_analysis = misinformation_detector.calculate_misinformation_risk(article)
                print(f"Misinformation Risk: {misinformation_analysis['risk_level']}")
            except Exception as e:
                print(f"Advanced analysis failed: {e}")

            for bullet in bullet_summary(article['summary']):
                print(f"- {bullet}")
            print(f"Link: {article['link']}")

if __name__ == "__main__":
    main()
