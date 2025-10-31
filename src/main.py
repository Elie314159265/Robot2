"""
Main Robot Control Program
Integrates all modules for ball tracking and blocking
"""

import sys
import os
import logging
import argparse
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main program entry point"""
    parser = argparse.ArgumentParser(
        description="Robot PK - 4-legged Goalkeeper Robot"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--phase",
        type=int,
        default=1,
        help="Development phase (1-8)"
    )
    parser.add_argument(
        "--test-camera",
        action="store_true",
        help="Run camera test"
    )
    parser.add_argument(
        "--test-detection",
        action="store_true",
        help="Run detection test"
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"Starting Robot PK (Phase {args.phase})")

    # Placeholder - actual implementation will be added in phases
    logger.info("Application initialized successfully")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
