
# Market Sentiment Heatmap Documentation

## Overview
The market sentiment heatmap provides real-time visualization of market sentiment across multiple cryptocurrencies using D3.js.

## Components

### Backend Services
- `sentiment_service.py`: Aggregates sentiment data
- API endpoint: `/api/market_sentiment`
- Configurable time ranges: 1h, 24h, 7d, 30d

### Frontend Visualization
- D3.js heatmap implementation
- Real-time WebSocket updates
- Customizable color scales
- Interactive tooltips

## Implementation Details

### Sentiment Calculation
```python
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

### Multi-Token Comparison
- Supports up to 20 tokens simultaneously
- Normalized sentiment scores (0-100)
- Color-coded visualization
- Comparative analysis features

## API Endpoints

### Get Market Sentiment
```
GET /api/market_sentiment
Query params:
- timerange: (1h|24h|7d|30d)
- tokens: comma-separated list of token symbols
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
```
