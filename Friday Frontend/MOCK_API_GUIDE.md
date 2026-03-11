# Mock API Development Guide

## 🎯 What is the Mock API?

The Mock API allows you to **develop and test the frontend completely without a backend server**. It simulates realistic API responses and behavior, making it perfect for:

- ✅ Frontend development
- ✅ Testing UI components
- ✅ Designing features
- ✅ Demo purposes

## 🚀 Getting Started with Mock API

Your `.env.local` already has Mock API enabled:

```bash
NEXT_PUBLIC_USE_MOCK_API=true
```

**That's it!** Just reload your frontend and it will use the mock API.

### Console Output

When using the mock API, you'll see logs like:

```
[🤖 Robot Service] Initialized with:
   API URL: http://localhost:8000
   Mock API: ✅ ENABLED (Development)

[Mock API] GET /api/status
[Mock API] POST /api/power {"isPoweredOn": true}
[Mock API] POST /api/listen
```

## 🎮 Mock API Features

### Simulated Robot State
- Power on/off
- Microphone toggle
- Volume control
- Status tracking

### Realistic Behavior
- Network latency delays (300ms default)
- Speaking simulation (2 seconds)
- Listening simulation (3 seconds)
- Voice command responses

### Stateful
- Changes persist during session
- Robot remembers last command
- Stats can be updated

## 🔄 Switching Between Mock and Real API

### Use Mock API (Development)
```bash
# .env.local
NEXT_PUBLIC_USE_MOCK_API=true
```

### Use Real Backend (Production)
```bash
# .env.local
NEXT_PUBLIC_USE_MOCK_API=false
```

> **Tip**: Make sure your backend is running at `http://localhost:8000` before switching to the real API.

## 📊 Mock API Endpoints

All these work automatically with mock data:

```
GET    /api/status    → Returns mock robot status
POST   /api/power     → Toggles power state
POST   /api/mic       → Toggles microphone
POST   /api/volume    → Toggles volume
POST   /api/speak     → Simulates speaking
POST   /api/listen    → Simulates listening
```

## 🧪 Testing Different Scenarios

### 1. Test Power Toggle
- Click the power button
- Button should toggle between "Online" and "Offline"
- All controls disabled when robot is offline

### 2. Test Microphone & Volume
- Toggle mic and volume buttons
- Status indicators should change color
- Speaking should fail if volume is off

### 3. Test Speaking
- Click speak button
- Avatar should animate
- Status shows "🗣️ Friday is speaking..."
- Lasts ~2 seconds

### 4. Test Listening
- Turn on mic first
- Click listen button
- Mock will simulate recording for ~3 seconds
- Last command should update with a simulated voice input

## 🔌 When to Switch to Real Backend

Switch to the real API when:

1. ✅ Your backend server is fully developed
2. ✅ All endpoints are implemented
3. ✅ CORS is configured on backend
4. ✅ You want to test real functionality

**Steps to switch:**

```bash
# 1. Update .env.local
NEXT_PUBLIC_USE_MOCK_API=false

# 2. Make sure backend is running
python app.py  # or your backend start command

# 3. Verify it's on port 8000
curl http://localhost:8000/health

# 4. Reload frontend
```

## 💡 Pro Tips

1. **Check browser console** - See all mock API calls logged
2. **No network errors** - Mock API never fails (perfect for testing UI)
3. **Fast responses** - Mock API is instant (except simulated delays)
4. **Stateful data** - Changes persist during your session
5. **Easy debugging** - See exactly what data is being used

## 🐛 Troubleshooting

### Mock API still showing network errors?
- Check in browser console for `[🤖 Robot Service]` log
- Verify `NEXT_PUBLIC_USE_MOCK_API=true` in `.env.local`
- Reload the page with hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

### Want to use real backend but getting errors?
- Start your backend: `python app.py`
- Set `NEXT_PUBLIC_USE_MOCK_API=false`
- Check if backend is on port 8000: `curl http://localhost:8000/health`

### Need to reset mock state?
- Hard refresh the page (Ctrl+Shift+R)
- Mock state resets on page reload

## 📝 Example: Checking Console Logs

Open Browser DevTools (F12) and look for:

```
✅ Mock API is working:
[🤖 Robot Service] Initialized with:
   API URL: http://localhost:8000
   Mock API: ✅ ENABLED (Development)

[Mock API] GET /api/status
[Mock API] POST /api/power {"isPoweredOn": true}
```

❌ If you see "Network error", make sure:
1. `NEXT_PUBLIC_USE_MOCK_API=true` is set
2. You reloaded the page
3. Check the `[🤖 Robot Service]` initialization logs

## 🎉 You're Ready!

The frontend is now fully functional with the mock API. All buttons work, all animations display, and you can test the entire UI!

When your backend is ready, just set `NEXT_PUBLIC_USE_MOCK_API=false` and point to your real API.

**Happy coding!** 🚀
