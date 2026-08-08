# backend/Dockerfile
FROM python:3.11-slim

# ffmpeg is required by whisperx (audio processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching -> faster rebuilds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright needs its own browser binaries downloaded separately from the pip package.
# --with-deps also installs the system libraries (fonts, codecs, etc.) Chromium needs
# to actually launch inside a slim Linux container.
RUN playwright install --with-deps chromium

# Now copy the actual code
COPY backend ./backend

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
