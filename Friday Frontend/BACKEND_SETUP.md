# Backend Setup Guide - Erovoutika Humanoid

This guide will help you get the backend server running so the frontend can communicate with it.

## Network Error: Could not reach the server

If you're seeing this error, follow these steps:

### 1. **Check Backend Server Status**

The error indicates your backend server is not running. Verify:

```bash
# Check if something is running on port 8000
netstat -tuln | grep 8000

# Or on macOS:
lsof -i :8000
```

### 2. **Start Your Backend Server**

Depending on your backend technology:

#### **If using Python (Flask/FastAPI):**
```bash
# Navigate to your backend directory
cd backend/

# Make sure you have dependencies installed
pip install -r requirements.txt

# Start the server
python app.py
# or for FastAPI:
uvicorn main:app --reload --port 8000
```

#### **If using Node.js/Express:**
```bash
cd backend/

npm install

npm start  # or npm run dev
```

#### **If using Docker:**
```bash
docker run -p 8000:8000 your-backend-image
```

### 3. **Test Backend Connectivity**

You can verify the backend is running:

```bash
# Test with curl
curl http://localhost:8000/api/status

# Or in VS Code terminal:
curl http://localhost:8000/health
```

### 4. **Update Environment Variables**

Make sure `.env.local` is configured correctly:

```bash
# .env.local should contain:
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENV=development
```

### 5. **Check CORS Configuration**

Your backend should allow requests from `http://localhost:3000`:

#### **Express.js:**
```javascript
const cors = require('cors');
app.use(cors({
  origin: 'http://localhost:3000',
  credentials: true
}));
```

#### **Flask:**
```python
from flask_cors import CORS
CORS(app, origins=["http://localhost:3000"])
```

#### **FastAPI:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 6. **Check Backend Required Endpoints**

Your backend should expose these endpoints:

```
GET    /health              - Health check
GET    /api/status          - Get robot status
POST   /api/power           - Toggle power
POST   /api/mic             - Toggle microphone
POST   /api/volume          - Toggle volume
POST   /api/speak           - Speak text
POST   /api/listen          - Start listening
```

### 7. **Enable Debug Logging**

The frontend now has enhanced logging. Check your browser console:

```
[API Request] GET http://localhost:8000/api/status
[API Error] Network Error - Backend server is unreachable
[Debugging Checklist]
...
```

### 8. **Verify in Docker/Network**

If using Docker Compose:

```yaml
version: '3'
services:
  frontend:
    build: .
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
  
  backend:
    build: ./backend
    ports:
      - "8000:8000"
```

## Common Issues

### Issue: "Could not reach the server"
- **Solution**: Start your backend server first, then start the frontend

### Issue: CORS errors in console  
- **Solution**: Add CORS middleware to your backend (see step 5)

### Issue: Timeout errors
- **Solution**: Backend is running but slow. Increase `REQUEST_TIMEOUT` in `robotService.ts`

### Issue: 404 errors on endpoints
- **Solution**: Verify your backend has all required endpoints

## Frontend Features Added

✅ **Automatic Retry Logic** - Will retry failed requests  
✅ **Health Check** - Verifies backend is accessible  
✅ **Enhanced Error Messages** - Shows exact steps to fix issues  
✅ **Debug Logging** - Logs all API requests/responses  
✅ **Timeout Protection** - Prevents hanging requests  

Check your browser console for detailed debugging information!
