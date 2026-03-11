<div align="center">

# 🤖 FRIDAY — Frontend

**The UI interface for the FRIDAY Voice Assistant**

![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

</div>

---

## ⚙️ Configuration (Important!)

Before running the frontend, you need to set the **IP address of the machine running the backend.**

Open this file:

```
src/config.ts
```

Edit these values:

```typescript
export const BACKEND_URL = "http://YOUR_IP_HERE:8000";
export const API_URL = "http://YOUR_IP_HERE:8000/api";
```

### 🔍 How to find your IP address

**On Windows**, open Command Prompt and run:

```bash
ipconfig
```

Look for **IPv4 Address** under your active network adapter.

Example:

```
IPv4 Address. . . . . . . . . . . : 192.168.1.100
```

Then update `config.ts`:

```typescript
export const BACKEND_URL = "http://192.168.1.100:8000";
export const API_URL = "http://192.168.1.100:8000/api";
```

---

## 🚀 Running the Frontend

Make sure the **FRIDAY Backend is running first**, then:

```bash
npm install
npm run dev
```

---

## 📋 Requirements

- Node.js >= 16
- FRIDAY Backend running on the same network

---

## 📄 License

MIT License — Created by [Railey29](https://github.com/Railey29)
