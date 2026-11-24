# Development image: Django dev server with live reload (source is bind-mounted by docker compose).
# Milestone 8 adds a separate production stage (gunicorn, static files, no dev dependencies).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /uvx /bin/

# The virtualenv lives outside /app so the bind-mount of ./backend over /app doesn't hide it.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .

# On Linux, bind-mounted files keep the host owner, so the dev user must share your UID to write
# migrations and coverage files. Set APP_UID/APP_GID in .env (see .env.example); macOS doesn't need it.
ARG APP_UID=10001
ARG APP_GID=10001
RUN groupadd --gid "$APP_GID" app \
    && useradd --uid "$APP_UID" --gid "$APP_GID" --create-home app \
    && mkdir -p /app/media \
    && chown -R app /app
USER app

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
