# Simple container for the admin panel (FastAPI)
# Note: Discord bot is typically deployed as a separate worker process.

FROM python:3.13-slim

WORKDIR /app

# Install deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY bot /app/bot
COPY panel /app/panel
COPY README.md /app/README.md

# Runtime env defaults (can be overridden by the platform)
ENV PANEL_HOST=0.0.0.0
ENV PORT=8080
ENV DATABASE_PATH=/app/data/bot.sqlite

EXPOSE 8080

CMD ["python", "-m", "panel.server"]
