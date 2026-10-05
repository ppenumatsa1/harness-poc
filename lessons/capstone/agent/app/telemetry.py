"""Lesson 10: OpenTelemetry -> App Insights. No-op when no connection string is set."""

import logging

from opentelemetry import trace

from . import config

tracer = trace.get_tracer("checkout-investigator.agent")


def setup(app=None) -> None:
    if not config.APPINSIGHTS:
        logging.getLogger(__name__).warning("APPLICATIONINSIGHTS_CONNECTION_STRING not set: telemetry off")
        return
    from azure.monitor.opentelemetry import configure_azure_monitor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    configure_azure_monitor(connection_string=config.APPINSIGHTS, logger_name="checkout")
    for noisy in ("azure.core.pipeline.policies.http_logging_policy", "azure.monitor.opentelemetry.exporter"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    if app is not None:
        FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
