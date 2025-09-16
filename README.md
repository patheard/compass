# Compass

A platform that will provide automated security assessment tools. For now it does next to nothing since it's very much a work in progress.

## Local
Add your secrets to a `.env` file.

```sh
cp .env.example .env
make dev
```

## Google OAuth
Your Google OAuth 2.0 client ID should be setup like so:
- `Authorized JavaScript origins`: http://localhost:8000
- `Authorized redirect URIs`: http://localhost:8000/auth/callback
