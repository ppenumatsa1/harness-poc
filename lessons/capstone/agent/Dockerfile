FROM python:3.12-slim

# az CLI: AzureCliCredential gets the Foundry token from your mounted `az login` (no API key).
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -sL https://aka.ms/InstallAzureCLIDeb | bash \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

RUN useradd --uid 1000 --create-home app
WORKDIR /srv
COPY pyproject.toml ./
# Local laptop: public PyPI fails the TLS handshake inside containers; use the approved Microsoft mirror.
# The mirror lacks github-copilot-sdk 1.0.16 final, so that wheel is vendored in ./wheels (fetched on the host).
# Override with --build-arg PIP_FEED=https://pypi.org/simple/ elsewhere (do not force the mirror on Hosted Agents).
ARG PIP_FEED=https://packagefeedproxy.microsoft.io/pypi/simple/
COPY wheels ./wheels
RUN UV_INDEX_URL=$PIP_FEED uv pip install --system --no-cache --find-links ./wheels -r pyproject.toml pytest

USER app
ENV HOME=/home/app AZURE_CONFIG_DIR=/home/app/.azure PYTHONUNBUFFERED=1
# Create the session-state dir as `app`, so the named volume mounted here inherits this owner.
RUN mkdir -p /home/app/.copilot
# Download the Copilot runtime at build time, not on first request.
RUN python -c "from copilot._cli_download import download_cli; print(download_cli())"

COPY --chown=app entrypoint.sh /entrypoint.sh
COPY --chown=app app ./app
COPY --chown=app tests ./tests
EXPOSE 8001
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
