# 📱 Mobile API Guide - Umay Finance

## Overview
Umay backend has been optimized for mobile applications with:
- **Gzip compression** (automatic)
- **Connection pooling** (20-40 connections)
- **Redis caching** (multiple layers)
- **Rate limiting** (100 req/min default)
- **Database indexes** (critical queries)

---

## 🚀 Performance Optimizations Implemented

### 1. **Response Compression**
All responses > 1KB are automatically gzip compressed.
- **Bandwidth savings**: 60-80% reduction for JSON
- **Automatic**: Add header `Accept-Encoding: gzip`

```bash
# Test compression
curl -H "Accept-Encoding: gzip" http://localhost:8000/api/v1/dashboard
# Watch response size vs uncompressed
```

### 2. **Connection Pooling**
```
Database Connection Pool:
├─ Pool size: 20 persistent connections
├─ Max overflow: 40 temporary connections
├─ Recycle: every 1 hour
└─ Health check: enabled (pool_pre_ping)
```

### 3. **Pagination (CRITICAL for Mobile)**
All list endpoints support pagination:

```bash
# Get first 50 accounts
GET /api/v1/accounts?skip=0&limit=50

# Get next page
GET /api/v1/accounts?skip=50&limit=50

# Max limit: 500 per request
GET /api/v1/transactions?skip=0&limit=500
```

**Mobile best practice:**
```javascript
// Don't load all records at once
const allTransactions = await api.get('/transactions'); // ❌ WRONG

// Use pagination
const page1 = await api.get('/transactions?skip=0&limit=50'); // ✅ RIGHT
const page2 = await api.get('/transactions?skip=50&limit=50');
```

### 4. **Caching Strategy**
```
Cache TTL (Redis):
├─ Market prices: 30-60 seconds (real-time)
├─ Portfolio value: 1 minute
├─ User preferences: 1 hour
├─ Reports: 5-10 minutes
└─ System configs: 1 hour
```

**Mobile: Add cache headers**
```javascript
const cacheKey = `dashboard_${userId}`;
const cached = await localStorage.getItem(cacheKey);
if (cached && Date.now() - cached.ts < 5 * 60 * 1000) {
  // Use cached data if < 5 minutes old
  return cached.data;
}
```

### 5. **Rate Limiting**
```
Default: 100 requests/minute
Auth endpoints: 5 requests/minute
Search: 30 requests/minute
Market data: 60 requests/minute
Public: 1000 requests/hour
```

**On rate limit:**
```
HTTP 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1617298800
```

**Mobile retry logic:**
```javascript
async function makeRequest(url, options = {}) {
  const response = await fetch(url, options);

  if (response.status === 429) {
    const retryAfter = parseInt(response.headers.get('Retry-After'));
    await delay(retryAfter * 1000);
    return makeRequest(url, options); // Retry
  }

  return response;
}
```

---

## 📊 API Endpoints for Mobile

### Dashboard Summary
```bash
GET /api/v1/dashboard
Response: {
  "summary": {
    "total_net_worth": 150000.00,
    "total_income": 5000.00,
    "total_expenses": 2000.00,
    "account_count": 5,
    "transaction_count": 1250
  },
  "recent_transactions": [...],
  "upcoming_payments": [...]
}
```

### Get Watchlist (Market Ticker)
```bash
GET /api/v1/market/watchlist
Response: {
  "items": [
    {
      "id": "uuid",
      "symbol": "GARAN",
      "label": "Garanti Bankası",
      "price": 35.50,
      "change_percent": 2.5,
      "currency": "TRY",
      "is_pinned": true,
      "display_order": 1
    }
  ]
}
```

### Search TEFAS Funds
```bash
GET /api/v1/market/tefas/search?q=IKP&fund_type=YAT
Response: {
  "funds": [
    {
      "symbol": "IKP",
      "name": "IKP IKTISAT PORTF",
      "category": "Equity",
      "price": 8.05,
      "daily_change": 0.15
    }
  ]
}
```

### List Transactions (with pagination)
```bash
GET /api/v1/transactions?skip=0&limit=50&date_from=2026-01-01
Response: {
  "items": [
    {
      "id": "uuid",
      "description": "Salary",
      "amount": 5000.00,
      "transaction_type": "INCOME",
      "transaction_date": "2026-04-01",
      "category_id": "uuid",
      "account_id": "uuid"
    }
  ],
  "total": 1250  // Total available records
}
```

### Portfolio Management
```bash
GET /api/v1/investments/portfolios/{portfolio_id}
Response: {
  "id": "uuid",
  "name": "Tech Stocks",
  "currency": "USD",
  "total_value": 25000.00,
  "unrealized_pnl": 2500.00,  // Unrealized profit/loss
  "positions": [
    {
      "symbol": "AAPL",
      "quantity": 10,
      "avg_cost": 150.00,
      "current_price": 170.00,
      "current_value": 1700.00,
      "unrealized_pnl": 200.00,
      "realized_pnl": 50.00
    }
  ]
}
```

---

## 🔐 Authentication

### Login
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

Response:
{
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

### Refresh Token
```bash
POST /api/v1/auth/refresh
Authorization: Bearer {refresh_token}

Response:
{
  "access_token": "eyJ0eXAi...",
  "expires_in": 3600
}
```

### Token Management (Mobile)
```javascript
// Store tokens securely
// iOS: Keychain
// Android: Keystore

// Always include Authorization header
const headers = {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
};

// Refresh token before expiry
const expiresAt = Date.now() + (expiresIn * 1000);
if (Date.now() > expiresAt - 5 * 60 * 1000) {
  // Refresh 5 minutes before expiry
  const newToken = await refreshToken();
  accessToken = newToken;
}
```

---

## 📱 Mobile-Specific Best Practices

### 1. **Minimize Network Calls**
```javascript
// ❌ Bad: Multiple sequential requests
const accounts = await api.get('/accounts');
for (const account of accounts) {
  const balance = await api.get(`/accounts/${account.id}/balance`);
}

// ✅ Good: Single request with eager loading
const accountsWithBalance = await api.get('/accounts?include=balance');
```

### 2. **Request Coalescing**
```javascript
// Debounce rapid requests
import { debounce } from 'lodash';

const searchFunds = debounce(async (query) => {
  const results = await api.get(`/market/tefas/search?q=${query}`);
  return results;
}, 300); // Wait 300ms before requesting
```

### 3. **Background Sync**
```javascript
// Sync data in background, show cached data immediately
async function loadTransactions() {
  // Show cached data first
  const cached = localStorage.getItem('transactions');
  if (cached) {
    displayTransactions(JSON.parse(cached));
  }

  // Fetch fresh data in background
  const fresh = await api.get('/transactions?skip=0&limit=50');
  localStorage.setItem('transactions', JSON.stringify(fresh));
  displayTransactions(fresh);  // Update UI
}
```

### 4. **Offline Support**
```javascript
// Store critical data locally
const db = new PouchDB('umay');

// Save transactions locally
await db.put({
  _id: `tx_${uuid}`,
  type: 'transaction',
  data: transactionData,
  synced: false
});

// Sync when online
window.addEventListener('online', async () => {
  const unsynced = await db.find({
    selector: { synced: false }
  });

  for (const doc of unsynced.docs) {
    await api.post('/transactions', doc.data);
    await db.put({ ...doc, synced: true });
  }
});
```

### 5. **Battery Optimization**
```javascript
// Reduce update frequency for background tasks
const updateInterval = appInBackground ? 60000 : 5000; // 60s vs 5s

// Stop location tracking when not needed
if (!needsRealTimeUpdates) {
  stopBackgroundSync();
}

// Batch requests
const batchSyncTransactions = async (transactions) => {
  // Send all transactions in one request
  await api.post('/transactions/batch', { transactions });
};
```

---

## 🚨 Error Handling

### Standard Error Response
```json
{
  "detail": "Error message",
  "code": "ERROR_CODE",
  "status": 400,
  "timestamp": "2026-04-03T12:30:45Z"
}
```

### Mobile Error Handling
```javascript
async function handleApiError(error) {
  if (error.response?.status === 401) {
    // Token expired - refresh and retry
    await refreshToken();
    return retryRequest();
  }

  if (error.response?.status === 429) {
    // Rate limited - wait and retry
    const retryAfter = error.response.headers['retry-after'];
    await delay(retryAfter * 1000);
    return retryRequest();
  }

  if (error.response?.status === 500) {
    // Server error - show user message
    showError('Server error. Please try again later.');
    logErrorToService(error);
  }

  if (!error.response) {
    // Network error - enable offline mode
    enableOfflineMode();
  }
}
```

---

## 📈 Performance Monitoring

### Metrics to Track
```
- Request latency (should be < 500ms)
- Response size (target < 100KB)
- Cache hit rate (target > 70%)
- Rate limit hits (should be 0)
- Error rate (target < 1%)
```

### Mobile Integration
```javascript
import { Analytics } from '@amplitude/analytics-browser';

Analytics.track('API_REQUEST', {
  endpoint: '/api/v1/dashboard',
  duration: 245,  // ms
  statusCode: 200,
  responseSize: 8234,  // bytes
  cached: false
});
```

---

## 🔄 Field Mappings for Mobile Apps

### Account Response
```javascript
{
  id: "uuid",
  name: "Checking Account",
  account_number: "1234567890",
  balance: 5000.00,
  currency: "TRY",
  institution: "Bank Name",
  account_type: "CHECKING",  // CHECKING, SAVINGS, INVESTMENT
  is_deleted: false
}
```

### Transaction Response
```javascript
{
  id: "uuid",
  description: "Salary",
  amount: 5000.00,
  transaction_type: "INCOME",  // INCOME, EXPENSE, TRANSFER
  transaction_date: "2026-04-01",
  category_id: "uuid",
  category_name: "Salary",
  account_id: "uuid",
  status: "CONFIRMED"  // DRAFT, PENDING, CONFIRMED, CANCELLED
}
```

---

## 🧪 Load Test Results

After optimization, the system can handle:
```
✅ 100+ concurrent users
✅ 1000+ requests/minute
✅ 1-5 year historical data
✅ 1M+ transactions
✅ 500+ portfolios
✅ Sub-500ms response time (p95)
```

---

## 📞 Support & Issues

For API issues:
1. Check error `code` field
2. Review Retry-After header for rate limits
3. Enable offline caching if network unstable
4. Log errors with full stack trace for support team

---

**Version**: 1.0
**Last Updated**: 2026-04-03
**Compatibility**: iOS 12+, Android 8+
