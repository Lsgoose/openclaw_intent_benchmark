from pathlib import Path


def report_storage_root() -> Path:
    return Path(__file__).resolve().parent.parent


if __name__ == '__main__':
    print(report_storage_root())
