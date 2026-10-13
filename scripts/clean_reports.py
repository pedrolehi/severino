"""Script para limpar relatórios e screenshots de testes anteriores."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT_DIR / "reports"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"


def clean():
    count_files = 0
    if SCREENSHOTS_DIR.exists():
        for f in SCREENSHOTS_DIR.glob("*.png"):
            f.unlink()
            count_files += 1

    if REPORTS_DIR.exists():
        for ext in ("*.html", "*.json", "*.md"):
            for f in REPORTS_DIR.glob(ext):
                f.unlink()
                count_files += 1

    print(f"🧹 Limpeza concluída: {count_files} arquivo(s) de teste removido(s) de reports/.")


if __name__ == "__main__":
    clean()
