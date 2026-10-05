FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
RUN useradd --uid 1000 --create-home app
WORKDIR /srv
COPY pyproject.toml ./
# Local laptop: public PyPI fails TLS inside containers; use the approved Microsoft mirror (override elsewhere).
ARG PIP_FEED=https://packagefeedproxy.microsoft.io/pypi/simple/
RUN UV_INDEX_URL=$PIP_FEED uv pip install --system --no-cache -r pyproject.toml pytest

USER app
ENV PYTHONUNBUFFERED=1
COPY --chown=app app ./app
COPY --chown=app tests ./tests
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
