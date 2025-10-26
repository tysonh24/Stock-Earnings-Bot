# Stock Earnings Bot

An automated Twitter bot that monitors Yahoo Finance for new earnings call transcripts from major market indexes (Dow Jones, NASDAQ, S&P 500), generates AI-powered summaries using ChatGPT, and posts them as Twitter threads.

## Features

- 📊 **Multi-Index Monitoring**: Tracks 500+ companies across Dow Jones, NASDAQ, and S&P 500
- 🤖 **AI-Powered Summaries**: Uses ChatGPT-4 to generate comprehensive 5-tweet thread summaries
- 🐦 **Twitter Integration**: Automatically posts earnings summaries as threaded tweets
- 🔄 **Duplicate Prevention**: Tracks processed transcripts to avoid reposting
- ⏰ **Automated Scheduling**: Runs continuously with configurable check intervals

## Architecture

```
┌─────────────────────┐
│  Yahoo Finance API  │
│  (Earnings Data)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Check Earnings     │
│  for Each Company   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐      ┌─────────────────────┐
│  Company in Index?  │ ──→ │  Yes: Process       │
└─────────────────────┘      │  No:  Skip          │
                             └──────────┬──────────┘
                                        │
                                        ▼
                             ┌─────────────────────┐
                             │  Already Processed? │
                             └──────────┬──────────┘
                                        │
                                        ▼
                             ┌─────────────────────┐
                             │  Generate ChatGPT   │
                             │  Summary Prompt     │
                             └──────────┬──────────┘
                                        │
                                        ▼
                             ┌─────────────────────┐
                             │  Get ChatGPT        │
                             │  Response (5 Tweets)│
                             └──────────┬──────────┘
                                        │
                                        ▼
                             ┌─────────────────────┐
                             │  Post Twitter Thread│
                             │  (5 Tweets)         │
                             └──────────┬──────────┘
                                        │
                                        ▼
                             ┌─────────────────────┐
                             │  Mark as Processed  │
                             └─────────────────────┘
```

## Setup

### 1. Clone and Navigate to Project

```bash
cd Stock-Earnings-Bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Keys

Copy the configuration template:

```bash
cp config.json.template config.json
```

Edit `config.json` and add your API keys:

```json
{
    "openai_api_key": "sk-your-openai-key",
    "twitter_consumer_key": "your-consumer-key",
    "twitter_consumer_secret": "your-consumer-secret",
    "twitter_access_token": "your-access-token",
    "twitter_access_token_secret": "your-access-token-secret"
}
```

### 4. Get API Keys

#### OpenAI API Key
1. Go to https://platform.openai.com/
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key

#### Twitter API Keys
1. Go to https://developer.twitter.com/
2. Apply for a Twitter Developer account
3. Create a new app
4. Generate API keys and access tokens
5. Enable "Read and Write" permissions

### 5. Run the Bot

**Run once (check now):**
```bash
python bot.py --once
```

**Run continuously (check every 60 minutes):**
```bash
python bot.py
```

**Run with custom interval (check every 30 minutes):**
```bash
python bot.py --interval 30
```

## Configuration

### Check Interval

The bot can be configured to check for new earnings at different intervals:

- Default: 60 minutes
- Minimum: 1 minute (be careful with API rate limits)
- Maximum: Any interval you prefer

### Company List

The bot uses `Indexes Listed/combined-indexes.csv` which contains:
- **Dow Jones Index**: 30 stocks
- **NASDAQ Index**: 101 stocks  
- **S&P 500 Index**: 503 stocks
- **Total**: 517 unique stocks

You can modify this file to add/remove companies.

## How It Works

### 1. Earnings Detection

The bot scans Yahoo Finance for earnings calendar data:
```python
stock = yf.Ticker("AAPL")
earnings = stock.calendar  # Recent earnings dates
```

### 2. Company Matching

Checks if the ticker exists in `combined-indexes.csv`:
```python
if ticker in self.companies:
    # Process this company
```

### 3. Duplicate Prevention

Tracks processed transcripts in `processed_transcripts.json`:
```json
[
  {
    "ticker": "AAPL",
    "quarter": "Q3",
    "year": "2025",
    "link": "...",
    "timestamp": "2025-01-15T10:30:00"
  }
]
```

### 4. ChatGPT Summary Generation

Creates a structured prompt:
```
Company: Apple Inc.
Quarter: Q3 2025
Transcript Link: https://...

Please create a 5-tweet thread:
Tweet 1: Overall earnings summary
Tweet 2: Key metrics and performance
Tweet 3: Management commentary
Tweet 4: Strategic initiatives
Tweet 5: Future guidance
```

### 5. Twitter Thread Posting

Posts tweets sequentially as a thread:
```python
# First tweet (standalone)
tweet1 = api.update_status("Tweet 1")

# Subsequent tweets (replies)
tweet2 = api.update_status("Tweet 2", 
    in_reply_to_status_id=tweet1.id)

tweet3 = api.update_status("Tweet 3",
    in_reply_to_status_id=tweet2.id)
# ... etc
```

## Output Format

The bot generates 5-tweet threads with:

1. **Tweet 1**: Overall earnings summary (revenue, EPS, growth)
2. **Tweet 2**: Key financial metrics and performance highlights
3. **Tweet 3**: Management commentary on business outlook
4. **Tweet 4**: Strategic initiatives and market positioning
5. **Tweet 5**: Guidance for future quarters/years

Each tweet is optimized for Twitter's 280-character limit.

## Troubleshooting

### Rate Limiting

If you encounter rate limits:
- Increase the `--interval` value (e.g., `--interval 120`)
- Don't exceed your API tier limits

### API Errors

**OpenAI Errors:**
- Check your API key is valid
- Verify you have sufficient credits
- Check rate limits on your OpenAI plan

**Twitter Errors:**
- Verify API credentials
- Check app permissions (need Read + Write)
- Ensure you haven't exceeded rate limits

### No Earnings Found

- Earnings are typically released quarterly
- Not all companies report on the same schedule
- Check Yahoo Finance manually for recent earnings

## Advanced Usage

### Custom Prompt

Edit the `generate_prompt()` method in `bot.py` to customize the summary style.

### Filtering Companies

Edit `combined-indexes.csv` to monitor only specific companies.

### Different ChatGPT Model

Change the model in `get_chatgpt_summary()`:
```python
model="gpt-3.5-turbo"  # Faster, cheaper
model="gpt-4"          # Better quality (default)
```

## Requirements

- Python 3.8+
- OpenAI API account
- Twitter Developer account
- Internet connection

## Dependencies

- `yfinance`: Yahoo Finance data
- `pandas`: Data handling
- `openai`: ChatGPT API
- `tweepy`: Twitter API
- `requests`: HTTP requests

## License

MIT License - feel free to modify and use for your own projects.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Disclaimer

This bot is for educational purposes. Always comply with:
- Yahoo Finance Terms of Service
- OpenAI Terms of Service
- Twitter API Terms of Service
- Respect rate limits and API usage policies

## Support

For issues or questions:
- Check the troubleshooting section
- Review API documentation
- Ensure all credentials are correct
