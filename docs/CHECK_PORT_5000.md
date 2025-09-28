# How to Check if Port 5000 (AI API) is Working

## Quick Check

**Port 5000 is WORKING!** ✓

The AI API on port 5000 is an internal Docker container port and is working correctly. It's accessible through the Nginx proxy on port 8008.

## Testing Methods

### 1. Test via Nginx Proxy (RECOMMENDED)
Port 5000 is not directly exposed; it's accessed through Nginx on port 8008:

```bash
# Test health endpoint
curl http://localhost:8008/ai/api/health

# Expected response:
{"service":"ai-api","status":"ok"}
```

### 2. Check Docker Container Status
```bash
# Check if AI API container is running
docker ps --filter "name=ai-api"

# Should show:
# mind2-ai-api-1   Up X minutes   5000/tcp
```

### 3. View Container Logs
```bash
# Check API logs for errors
docker logs mind2-ai-api-1 --tail 50

# Look for:
# * "Running on http://0.0.0.0:5000"
# * No error messages
```

### 4. Test Other API Endpoints
```bash
# Test login endpoint
curl -X POST http://localhost:8008/ai/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'

# Test receipts endpoint (requires authentication)
curl http://localhost:8008/ai/api/receipts
```

### 5. Network Connectivity Test
```bash
# Check if port is listening inside container
docker exec mind2-ai-api-1 netstat -tuln | grep 5000
# OR
docker exec mind2-ai-api-1 ss -tuln | grep 5000
```

## Understanding the Architecture

```
[Client] → :8008 (Nginx) → /ai/api/* → :5000 (AI API Container)
```

- **Port 5000**: Internal container port (NOT directly accessible)
- **Port 8008**: Public access point via Nginx
- **Path prefix**: `/ai/api/` routes to the AI API

## Troubleshooting

### If API is not responding:

1. **Check container is running:**
   ```bash
   docker-compose ps ai-api
   ```

2. **Restart the service:**
   ```bash
   docker-compose restart ai-api
   ```

3. **Check for startup errors:**
   ```bash
   docker-compose logs ai-api --tail 100
   ```

4. **Verify environment variables:**
   ```bash
   docker exec mind2-ai-api-1 env | grep -E "DB_|REDIS_"
   ```

5. **Test database connection:**
   ```bash
   docker exec mind2-ai-api-1 python -c "from services.db.connection import get_db_connection; get_db_connection()"
   ```

## Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| Container not running | `docker-compose up -d ai-api` |
| Port 8008 not accessible | Check if Nginx is running: `docker ps \| grep nginx` |
| Authentication errors | Verify ADMIN_PASSWORD in .env file |
| Database connection failed | Check MySQL is running on port 3310 |
| Redis connection failed | Check Redis is running on port 6380 |

## Summary

Port 5000 is working correctly as an internal service port. Always access it through the Nginx proxy on port 8008 using the `/ai/api/` path prefix.