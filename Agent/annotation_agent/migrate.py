import logging

from .database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-migrate")


def main() -> int:
    logger.info("Creating tables in labelhub_agent if not exist...")
    init_db()
    logger.info("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())