import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict
import os

class DiscourseScraperTDS:
    def __init__(self, base_url: str = "https://discourse.onlinedegree.iitm.ac.in"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def scrape_discourse_posts(self, start_date: str, end_date: str, category_id: int = 123) -> List[Dict]:
        """
        Scrape TDS Discourse posts between given dates
        category_id 123 is typically for TDS course
        """
        posts = []
        
        try:
            # Convert date strings to datetime objects
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            # Get topics from the category
            category_url = f"{self.base_url}/c/degree-programs/tools-in-data-science/{category_id}.json"
            
            page = 0
            while page < 10:  # Limit to prevent infinite loop
                params = {'page': page}
                response = self.session.get(category_url, params=params)
                
                if response.status_code != 200:
                    print(f"Failed to fetch page {page}: {response.status_code}")
                    break
                
                data = response.json()
                topics = data.get('topic_list', {}).get('topics', [])
                
                if not topics:
                    break
                
                for topic in topics:
                    # Check if topic is within date range
                    created_at = datetime.strptime(topic['created_at'][:10], "%Y-%m-%d")
                    
                    if start_dt <= created_at <= end_dt:
                        post_data = self.scrape_topic_details(topic['id'])
                        if post_data:
                            posts.append(post_data)
                    
                    # Rate limiting
                    time.sleep(0.5)
                
                page += 1
            
            print(f"Scraped {len(posts)} posts from {start_date} to {end_date}")
            return posts
            
        except Exception as e:
            print(f"Error scraping discourse posts: {e}")
            return []
    
    def scrape_topic_details(self, topic_id: int) -> Dict:
        """Scrape detailed information from a specific topic"""
        try:
            topic_url = f"{self.base_url}/t/{topic_id}.json"
            response = self.session.get(topic_url)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            # Extract main post content
            posts = data.get('post_stream', {}).get('posts', [])
            if not posts:
                return None
            
            main_post = posts[0]
            
            post_data = {
                'id': topic_id,
                'title': data.get('title', ''),
                'url': f"{self.base_url}/t/{topic_id}",
                'content': self.clean_html(main_post.get('cooked', '')),
                'created_at': main_post.get('created_at', ''),
                'author': main_post.get('username', ''),
                'replies': []
            }
            
            # Extract replies
            for post in posts[1:5]:  # Get up to 4 replies
                reply = {
                    'content': self.clean_html(post.get('cooked', '')),
                    'author': post.get('username', ''),
                    'created_at': post.get('created_at', '')
                }
                post_data['replies'].append(reply)
            
            return post_data
            
        except Exception as e:
            print(f"Error scraping topic {topic_id}: {e}")
            return None
    
    def clean_html(self, html_content: str) -> str:
        """Clean HTML content and extract text"""
        if not html_content:
            return ""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove code blocks, quotes, etc. for cleaner text
        for element in soup(['code', 'pre', 'blockquote']):
            element.decompose()
        
        return soup.get_text().strip()
    
    def save_scraped_data(self, posts: List[Dict], filename: str = "scraped_discourse_data.json"):
        """Save scraped data to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(posts, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(posts)} posts to {filename}")
        except Exception as e:
            print(f"Error saving data: {e}")

def main():
    """Main function to run the scraper"""
    scraper = DiscourseScraperTDS()
    
    # Scrape posts from Jan 1, 2025 to Apr 14, 2025
    start_date = "2025-01-01"
    end_date = "2025-04-14"
    
    print(f"Starting to scrape TDS Discourse posts from {start_date} to {end_date}")
    posts = scraper.scrape_discourse_posts(start_date, end_date)
    
    if posts:
        scraper.save_scraped_data(posts)
        print("Scraping completed successfully!")
    else:
        print("No posts found or scraping failed.")

if __name__ == "__main__":
    main()
