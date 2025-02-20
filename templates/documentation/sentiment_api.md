
# Sentiment Analysis API Documentation

## Endpoints

### GET /api/sentiment/compare
Compare sentiment across multiple tokens.

**Parameters:**
- `tokens`: Comma-separated list of token symbols
- `timerange`: Analysis time range (1h, 24h, 7d, 30d)

**Response:**
```json
{
  "data": [
    {
      "token": "BTC",
      "sentiment_score": 75.5,
      "momentum": 0.8,
      "volume_change": 1.2,
      "social_score": 0.65
    }
  ]
}
```

### GET /api/sentiment/timerange
Get sentiment data for specific time ranges.

**Parameters:**
- `token`: Token symbol
- `from`: Start timestamp
- `to`: End timestamp

**Response:**
```json
{
  "data": [
    {
      "timestamp": 1645363200,
      "sentiment_score": 68.5
    }
  ]
}
```
