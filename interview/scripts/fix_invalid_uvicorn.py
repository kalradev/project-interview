"""
Remove invalid/corrupted 'uvicorn' distribution folder from site-packages.
Run with global Python when no uvicorn process is running:
  python -m scripts.fix_invalid_uvicorn
  or from interview/:  python scripts/fix_invalid_uvicorn.py
"""
import os
import shutil
import sys

def main():
    import site
    sp = site.getsitepackages()
    if not sp:
        sp = [site.USER_SITE] if site.USER_SITE else []
    removed = []
    for base in sp:
        if not os.path.isdir(base):
            continue
        for name in os.listdir(base):
            path = os.path.join(base, name)
            if not os.path.isdir(path):
                continue
            if name.startswith("-") and "vicorn" in name.lower():
                try:
                    shutil.rmtree(path)
                    removed.append(path)
                except OSError as e:
                    print(f"Could not remove {path}: {e}", file=sys.stderr)
    if removed:
        print("Removed invalid distribution(s):", removed)
    else:
        print("No invalid -vicorn distribution folder found in site-packages.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
