"""
Run arq worker for video generation tasks.
"""
import asyncio
from arq import run_worker
from worker.tasks import WorkerSettings


if __name__ == "__main__":
    run_worker(WorkerSettings)
