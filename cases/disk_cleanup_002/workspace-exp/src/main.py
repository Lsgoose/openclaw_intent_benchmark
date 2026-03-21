from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


if __name__ == '__main__':
    print(project_root())
