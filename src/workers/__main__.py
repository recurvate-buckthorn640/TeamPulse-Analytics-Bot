from src.workers.celery_app import celery_app


def main() -> None:
    celery_app.start()


if __name__ == "__main__":
    main()

