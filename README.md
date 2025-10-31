# Tohum v1 - Cekirdek Asistan

## Genel Bakis
Tohum v1; FastAPI tabanli bir backend, Next.js tabanli bir web arayuzu ve SQLite + ChromaDB destekli hafiza katmani ile calisan kisisel asistan prototipidir. Proje chat, sesli etkilesim ve uzun sureli hafiza yeteneklerini tek cati altinda toplar.

## Mimari
- **Backend:** FastAPI, REST + WebSocket uclari, ses (STT/TTS) hizmetleri, hafiza katmani.
- **Frontend:** Next.js, Tailwind CSS, Zustand; chat, ses ve hafiza panelleri.
- **Depolama:** SQLite (oturum ve mesajlar) + ChromaDB (vektor hafiza).

## Onkosullar
- Python 3.11+
- Node.js 20+
- FFmpeg (ses donusumleri icin)
- Gerekli modeller ve API anahtarlari (opsiyonel):
  - Piper model dosyasi (offline TTS profili icin)
  - OpenAI/OpenRouter anahtarlari (LLM entegrasyon planlari icin)

## Kurulum
### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp ../.env.example.env .env  # degerleri duzenleyin
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

## Onemli Ortam Degiskenleri
Backend `.env` dosyasi icin:
- `APP_NAME` - FastAPI basligi.
- `CORS_ORIGINS` - Frontend kaynaklari.
- `SQLITE_PATH` - SQLite dosyasi (varsayilan: `data/memory.sqlite`).
- `CHROMADB_PATH` - ChromaDB klasoru.
- `TTS_PROFILE` - `offline` (piper) veya `online` (gTTS).
- `PIPER_MODEL_PATH` / `PIPER_SPEAKER` - Piper ayarlari.
- `GTTS_LANGUAGE` - gTTS dili.
- `WHISPER_DEVICE`, `WHISPER_MODEL` - faster-whisper ayarlari.

Frontend `.env.local` icin:
- `NEXT_PUBLIC_API_BASE` - REST uclarinin tabani (ornegin `http://localhost:8000`).
- `NEXT_PUBLIC_WS_BASE` - WebSocket tabani (ornegin `ws://localhost:8000`).

## Hizli Test Akisi
1. `ffmpeg -version`, `python --version`, `node -v` ile onkosullari dogrulayin.
2. Backend'i `uvicorn main:app --host 0.0.0.0 --port 8000` komutu ile calistirin.
3. Saglik uclarini kontrol edin: `curl http://localhost:8000/health`, `curl http://localhost:8000/ready`.
4. Basit chat istegi: `curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"session_id":"demo","message":"Merhaba","mode":"text"}'`.
5. Hafizaya not ekleyin ve cagirin: `curl -X POST http://localhost:8000/api/memory/remember -H "Content-Type: application/json" -d '{"text":"Bugun 14:00 toplanti","tags":["takvim"]}'`.
6. Frontend'i `npm run dev` ile baslatin ve `http://localhost:3000` uzerinden kontrol edin.

## Notlar
- WebSocket ses hatti `ws://<API>/ws/voice` adresinde calisir. Mikrofon izni istemcide verilmelidir.
- `memory` servisindeki ChromaDB entegrasyonu, ilk calistirmada modeli indirmek icin internet baglantisi gerektirebilir.
- Log ve hata ayiklama icin FastAPI uygulamasini `--reload` ile baslatabilir, gerekirse `uvicorn` log seviyesini artirabilirsiniz.

## Lisans
Bu proje icin lisans bilgisini ekleyin.
