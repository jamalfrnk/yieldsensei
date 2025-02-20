sentiment_score = weighted_average([
    (price_momentum, 0.4),
    (volume_change, 0.3),
    (social_sentiment, 0.3)
])
```

### Time Range Configuration
- Default: 24h
- Available ranges: 1h, 24h, 7d, 30d
- Endpoint: `/api/market_sentiment?timerange=24h`

### Market Cap Limitation
- Displays only top 20 cryptocurrencies by market capitalization
- Automatically updates rankings based on current market data
- Provides focused view of major market movements

## API Endpoints

### Get Market Sentiment
```
GET /api/market_sentiment
Query params:
- timerange: (1h|24h|7d|30d)
Response: Array of top 20 cryptocurrencies with sentiment data
```

### WebSocket Updates
```
ws://your-domain/ws/sentiment
Message format: {
    token: string,
    sentiment_score: number,
    timestamp: number
}
```

## Usage Example
```javascript
// Initialize heatmap
const heatmap = new SentimentHeatmap('#heatmap-container', {
    timeRange: '24h',
    tokens: ['BTC', 'ETH', 'SOL'],
    colorScale: ['#ef4444', '#d1d5db', '#22c55e']
});

// Update time range
heatmap.updateTimeRange('7d');