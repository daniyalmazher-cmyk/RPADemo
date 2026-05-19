"""Robocorp entry point — Sensitive Data Discovery & Classification bot."""
from robocorp.tasks import task

from process import Process


@task
def main() -> None:
    process = Process()
    try:
        process.start()
    finally:
        process.finish()
