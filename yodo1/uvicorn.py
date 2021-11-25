import logging


class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return 'GET /health_check' not in record.getMessage()


def patch_uvicorn_logger() -> None:
    """
    Need to call this at @app.on_event("startup"), otherwise overwrite won't affect
    :return:
    """
    uvicorn_logger = logging.getLogger('uvicorn.access')
    if uvicorn_logger:
        for h in uvicorn_logger.handlers:
            uvicorn_logger.removeHandler(h)
        uvicorn_logger.addFilter(HealthCheckFilter())
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)-5s | %(message)s"))
        uvicorn_logger.addHandler(handler)
