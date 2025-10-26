#!/usr/bin/env python3
"""
Stock Earnings Bot
Monitors Yahoo Finance for new earnings call transcripts,
checks if company is in indexes, generates summary with ChatGPT,
and posts to Twitter as a thread.
"""

import yfinance as yf
import pandas as pd
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Optional
import openai
import tweepy
from pathlib import Path


class EarningsBot:
    def __init__(self, config_path: str = "config.json"):
        """Initialize the bot with configuration."""
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Load company index
        self.companies = self._load_companies()
        
        # Initialize APIs
        self.openai_client = openai.OpenAI(api_key=self.config['openai_api_key'])
        self.twitter_api = self._init_twitter()
        
        # Track processed transcripts
        self.processed_file = "processed_transcripts.json"
        self.processed = self._load_processed()
    
    def _load_companies(self) -> Dict[str, str]:
        """Load companies from combined index CSV."""
        df = pd.read_csv('Indexes Listed/combined-indexes.csv')
        return dict(zip(df['Ticker'], df['Company Name']))
    
    def _init_twitter(self):
        """Initialize Twitter API client."""
        auth = tweepy.OAuthHandler(
            self.config['twitter_consumer_key'],
            self.config['twitter_consumer_secret']
        )
        auth.set_access_token(
            self.config['twitter_access_token'],
            self.config['twitter_access_token_secret']
        )
        return tweepy.API(auth)
    
    def _load_processed(self) -> List[Dict]:
        """Load list of processed transcripts."""
        if os.path.exists(self.processed_file):
            with open(self.processed_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_processed(self):
        """Save processed transcripts list."""
        with open(self.processed_file, 'w') as f:
            json.dump(self.processed, f, indent=2)
    
    def _is_processed(self, ticker: str, quarter: str, year: str) -> bool:
        """Check if transcript has been processed."""
        for item in self.processed:
            if (item['ticker'] == ticker and 
                item['quarter'] == quarter and 
                item['year'] == year):
                return True
        return False
    
    def _mark_processed(self, ticker: str, quarter: str, year: str, link: str):
        """Mark transcript as processed."""
        self.processed.append({
            'ticker': ticker,
            'quarter': quarter,
            'year': year,
            'link': link,
            'timestamp': datetime.now().isoformat()
        })
        self._save_processed()
    
    def check_earnings_data(self, ticker: str) -> Optional[Dict]:
        """
        Check if company has new earnings data.
        Returns dict with earnings info if available.
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get earnings calendar
            earnings_calendar = stock.calendar
            
            if earnings_calendar is not None and not earnings_calendar.empty:
                # Get most recent earnings date
                latest_date = earnings_calendar.index[-1]
                quarter = self._get_quarter(latest_date)
                year = latest_date.year
                
                return {
                    'ticker': ticker,
                    'company_name': info.get('longName', ticker),
                    'quarter': quarter,
                    'year': year,
                    'earnings_date': latest_date.strftime('%Y-%m-%d'),
                    'link': f"https://finance.yahoo.com/quote/{ticker}/events?p={ticker}"
                }
        except Exception as e:
            print(f"Error checking earnings for {ticker}: {e}")
        
        return None
    
    def _get_quarter(self, date) -> str:
        """Convert date to quarter string."""
        month = date.month
        if month in [1, 2, 3]:
            return "Q1"
        elif month in [4, 5, 6]:
            return "Q2"
        elif month in [7, 8, 9]:
            return "Q3"
        else:
            return "Q4"
    
    def generate_prompt(self, company_name: str, quarter: str, year: str, link: str) -> str:
        """Generate ChatGPT prompt for earnings summary."""
        return f"""You are analyzing an earnings call transcript for a stock market bot. 

Company: {company_name}
Quarter: {quarter} {year}
Transcript Link: {link}

Please create a comprehensive 5-tweet thread summary of the key points from this earnings call. For each tweet:

Tweet 1: Overall earnings summary (revenue, EPS, growth)
Tweet 2: Key financial metrics and performance highlights
Tweet 3: Management commentary on business outlook
Tweet 4: Strategic initiatives and market positioning
Tweet 5: Guidance for future quarters/years

Format your response as a JSON array with exactly 5 objects, each with a "tweet" field containing the tweet text.
Keep each tweet under 280 characters including hashtags.

Example format:
{{
  "tweets": [
    {{"tweet": "Summary tweet 1"}},
    {{"tweet": "Summary tweet 2"}},
    {{"tweet": "Summary tweet 3"}},
    {{"tweet": "Summary tweet 4"}},
    {{"tweet": "Summary tweet 5"}}
  ]
}}

Analyze the transcript at the link and generate the thread."""

    def get_chatgpt_summary(self, prompt: str) -> Optional[List[str]]:
        """Get summary from ChatGPT API."""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a financial analyst that summarizes earnings call transcripts for Twitter."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            result = response.choices[0].message.content
            
            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return [item['tweet'] for item in data['tweets']]
            
            # Fallback: return raw response split into 5 parts
            # (in case JSON parsing fails)
            return self._split_into_tweets(result, 5)
            
        except Exception as e:
            print(f"Error getting ChatGPT summary: {e}")
            return None
    
    def _split_into_tweets(self, text: str, n_tweets: int) -> List[str]:
        """Split text into approximately N tweets."""
        # Simple splitting logic - could be improved
        sentences = text.split('. ')
        tweets = []
        current_tweet = ""
        
        for sentence in sentences:
            if len(current_tweet) + len(sentence) < 260:
                current_tweet += sentence + ". "
            else:
                if current_tweet:
                    tweets.append(current_tweet.strip())
                current_tweet = sentence + ". "
        
        if current_tweet and len(tweets) < n_tweets:
            tweets.append(current_tweet.strip())
        
        return tweets[:n_tweets]
    
    def post_twitter_thread(self, tweets: List[str]) -> bool:
        """Post tweets as a thread to Twitter."""
        try:
            # Post first tweet
            status = self.twitter_api.update_status(tweets[0])
            previous_tweet = status
            
            # Post remaining tweets as replies
            for tweet_text in tweets[1:]:
                status = self.twitter_api.update_status(
                    status=tweet_text,
                    in_reply_to_status_id=previous_tweet.id,
                    auto_populate_reply_metadata=True
                )
                previous_tweet = status
                time.sleep(1)  # Rate limiting
            
            return True
        except Exception as e:
            print(f"Error posting to Twitter: {e}")
            return False
    
    def run_once(self):
        """Run one check cycle."""
        print(f"Checking earnings data at {datetime.now()}")
        
        for ticker, company_name in self.companies.items():
            print(f"Checking {ticker} - {company_name}...")
            
            try:
                earnings_info = self.check_earnings_data(ticker)
                
                if earnings_info:
                    quarter = earnings_info['quarter']
                    year = str(earnings_info['year'])
                    
                    # Check if already processed
                    if not self._is_processed(ticker, quarter, year):
                        print(f"New earnings found for {ticker}!")
                        
                        # Generate summary
                        prompt = self.generate_prompt(
                            earnings_info['company_name'],
                            quarter,
                            year,
                            earnings_info['link']
                        )
                        
                        tweets = self.get_chatgpt_summary(prompt)
                        
                        if tweets:
                            print(f"Posting thread for {ticker}...")
                            success = self.post_twitter_thread(tweets)
                            
                            if success:
                                self._mark_processed(
                                    ticker,
                                    quarter,
                                    year,
                                    earnings_info['link']
                                )
                                print(f"Successfully posted thread for {ticker}")
                        else:
                            print(f"Failed to generate summary for {ticker}")
                
                # Rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing {ticker}: {e}")
                continue
    
    def run_continuous(self, interval_minutes: int = 60):
        """Run bot continuously, checking every interval_minutes."""
        print(f"Starting bot. Checking every {interval_minutes} minutes.")
        
        while True:
            try:
                self.run_once()
                print(f"Next check in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                print("\nBot stopped by user.")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(interval_minutes * 60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Stock Earnings Bot')
    parser.add_argument('--config', default='config.json', help='Path to config file')
    parser.add_argument('--once', action='store_true', help='Run once instead of continuously')
    parser.add_argument('--interval', type=int, default=60, help='Check interval in minutes')
    
    args = parser.parse_args()
    
    bot = EarningsBot(config_path=args.config)
    
    if args.once:
        bot.run_once()
    else:
        bot.run_continuous(interval_minutes=args.interval)


if __name__ == "__main__":
    main()

