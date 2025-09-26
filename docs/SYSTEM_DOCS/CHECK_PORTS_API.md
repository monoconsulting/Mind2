# Port API - Quick Reference

**API Server:** `http://localhost:8199` (Atlas Main Application)

Simple port management for Docker containers. Use these 4 endpoints:

## 1. Get All Ports
**Get a list of all ports in the system**
```bash
GET http://localhost:8199/api/ports
```
Returns all registered ports with project info.

## 2. Check Port Status
**Is this port free or busy?**
```bash
GET http://localhost:8199/api/ports
# Then check if your port number exists in the response
```
If port number appears in the list = BUSY. If not = FREE.

## 3. Get Available Ports
**Get a list of all free ports (ranges)**
```bash
GET http://localhost:8199/api/ports
# Free ports = any port NOT in the response list
# Common ranges: 3000-3999, 8000-8999, 9000-9999
```

## 4. Register New Port
**Register a new port**
```bash
POST http://localhost:8199/api/ports
Content-Type: application/json

{
  "project_id": 1,
  "port": 8080,
  "service_name": "web"
}
```

## Complete Examples

### Check if port 8080 is free:
```javascript
fetch('http://localhost:8199/api/ports')
  .then(res => res.json())
  .then(data => {
    const busy = data.ports.some(p => p.port === 8080);
    console.log(busy ? 'Port 8080 is BUSY' : 'Port 8080 is FREE');
  });
```

### Register port 8080 for your web service:
```javascript
fetch('http://localhost:8199/api/ports', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    project_id: 1,
    port: 8080,
    service_name: 'web'
  })
});
```

### Find all free ports in range 8000-8100:
```javascript
fetch('http://localhost:8199/api/ports')
  .then(res => res.json())
  .then(data => {
    const usedPorts = data.ports.map(p => p.port);
    const freePorts = [];
    for (let port = 8000; port <= 8100; port++) {
      if (!usedPorts.includes(port)) {
        freePorts.push(port);
      }
    }
    console.log('Free ports:', freePorts);
  });
```

## API Response Format
```json
{
  "ok": true,
  "ports": [
    {
      "port": 8080,
      "service_name": "web",
      "project_name": "MyApp"
    }
  ]
}
```

That's it! Just 4 simple operations for port management.