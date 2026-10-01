"""Simplified high-intent search query generator."""
import urllib.parse
from typing import Dict, List

def build_search_urls(query: str) -> Dict[str, str]:
    encoded = urllib.parse.quote_plus(query)
    return {
        "Google": f"https://www.google.com/search?q={encoded}",
        "DuckDuckGo": f"https://duckduckgo.com/?q={encoded}",
        "Bing": f"https://www.bing.com/search?q={encoded}"
    }

def generate_dorks(national_number: str, e164_number: str) -> List[Dict]:
    clean_national = national_number.replace(" ", "").replace("-", "")
    
    categories = [
        {
            "category": "General Footprint",
            "queries": [
                {
                    "title": "Exact match (National format)",
                    "query": f'"{clean_national}"',
                    "urls": build_search_urls(f'"{clean_national}"')
                },
                {
                    "title": "Exact match (E.164 international)",
                    "query": f'"{e164_number}"',
                    "urls": build_search_urls(f'"{e164_number}"')
                }
            ]
        },
        {
            "category": "Social & Profiles",
            "queries": [
                {
                    "title": "LinkedIn Profiles",
                    "query": f'site:linkedin.com/in "{clean_national}"',
                    "urls": build_search_urls(f'site:linkedin.com/in "{clean_national}"')
                },
                {
                    "title": "Facebook Profiles",
                    "query": f'site:facebook.com "{clean_national}"',
                    "urls": build_search_urls(f'site:facebook.com "{clean_national}"')
                },
                {
                    "title": "Instagram / Threads",
                    "query": f'site:instagram.com "{clean_national}"',
                    "urls": build_search_urls(f'site:instagram.com "{clean_national}"')
                }
            ]
        },
        {
            "category": "Business & Trade",
            "queries": [
                {
                    "title": "Justdial Directory",
                    "query": f'site:justdial.com "{clean_national}"',
                    "urls": build_search_urls(f'site:justdial.com "{clean_national}"')
                },
                {
                    "title": "IndiaMART Listings",
                    "query": f'site:indiamart.com "{clean_national}"',
                    "urls": build_search_urls(f'site:indiamart.com "{clean_national}"')
                }
            ]
        },
        {
            "category": "Public Records & Dumps",
            "queries": [
                {
                    "title": "PDF / Docs Mentioning Number",
                    "query": f'filetype:pdf "{clean_national}"',
                    "urls": build_search_urls(f'filetype:pdf "{clean_national}"')
                },
                {
                    "title": "Pastebin & Data Text Dumps",
                    "query": f'site:pastebin.com "{clean_national}"',
                    "urls": build_search_urls(f'site:pastebin.com "{clean_national}"')
                }
            ]
        }
    ]
    return categories
