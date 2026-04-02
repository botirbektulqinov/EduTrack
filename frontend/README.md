# EduTrack Frontend

React 19 + TypeScript + Vite frontend for EduTrack.

## Commands

```powershell
npm ci
npm run dev:h
npm run lint
npm run build
```

## Runtime behavior

- The app calls the backend through `/api/v1`
- WebSocket proctoring uses `/ws`
- In development, Vite proxies both paths to `http://127.0.0.1:8000`
- In production, `frontend/nginx.conf` proxies both paths to the `api` container
- Optional env overrides live in `frontend/.env.example`
