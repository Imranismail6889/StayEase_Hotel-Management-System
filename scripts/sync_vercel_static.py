"""Copy Flask frontend assets into Vercel's CDN-served public directory."""

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app" / "static"
DESTINATION = ROOT / "public" / "static"


def main():
    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for folder in ("css", "js"):
        shutil.copytree(SOURCE / folder, DESTINATION / folder)


if __name__ == "__main__":
    main()
