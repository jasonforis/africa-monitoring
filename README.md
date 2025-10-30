# 🌍 Africa Monitoring Dashboard

Real-time monitoring of African countries news with AI-generated summaries.

## Features

- 📊 **Real-time monitoring** of 54+ African countries
- 🤖 **AI-generated summaries** for each country
- 📈 **Ranking by mentions** in last 24 hours
- 🔄 **Hourly updates** with fresh data
- 🎨 **Beautiful UI** with country flags and interactive cards

## Tech Stack

- **Backend:** Node.js (web server)
- **Data Collection:** Python 3 (API scraping & AI generation)
- **AI:** OpenRouter API (GPT-4 for summaries)
- **Deployment:** Railway

## Environment Variables

```
OPENROUTER_API_KEY=your_api_key_here
PORT=3001
```

## Local Development

```bash
# Install dependencies (none required for Node.js server)
npm install

# Generate initial data
python3 africa_monitor.py

# Start server
npm start
```

## Deployment

Deploy to Railway:
1. Connect this repository
2. Set environment variables
3. Railway will automatically detect and run `npm start`

## Data Update

The monitoring data is updated hourly via `africa_monitor.py` script which:
1. Fetches data from beta.index.ru API (all African countries)
2. Generates AI summaries for each country
3. Saves to `africa_monitoring.json`

## License

MIT

