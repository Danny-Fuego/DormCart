import sqlite3
from pathlib import Path

# Resolve project paths relative to this script (keeps it portable)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "dormcart.db"

# Where the demo product images live on disk + how they are referenced in templates
IMAGES_DIR = BASE_DIR / "static" / "uploads" / "products"
URL_PREFIX = "/static/uploads/products"


def main():
    # Safety check so the script fails fast with a clear message
    if not IMAGES_DIR.exists():
        raise SystemExit(f"Folder not found: {IMAGES_DIR}")

    # Collect image files (only common web image formats) and sort for consistent ordering
    image_files = sorted([
        p for p in IMAGES_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
    ])

    if not image_files:
        raise SystemExit("No images found in the folder.")

    # Convert file names into URLs that Flask can serve from /static/...
    image_urls = [f"{URL_PREFIX}/{p.name}" for p in image_files]

    # Print what was found (useful during setup/debugging)
    print(f"Found {len(image_urls)} images:")
    for u in image_urls:
        print(" -", u)

    # Connect to SQLite and enable foreign keys (SQLite requires PRAGMA per connection)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")

    # Pull all product ids in a stable order so seeding stays predictable
    product_ids = [r["id"] for r in cur.execute("SELECT id FROM products ORDER BY id").fetchall()]
    if not product_ids:
        raise SystemExit("No products found. Seed products first.")

    # Duplicate-protection: if product_images already has any rows, exit to avoid re-seeding
    #
    # (ChatGPT helped me think through a simple idempotent approach so re-running the
    # script doesn't duplicate rows in product_images.)
    existing = cur.execute("SELECT 1 FROM product_images LIMIT 1;").fetchone()
    if existing:
        raise SystemExit("product_images already has rows. Skipping to avoid duplicates.")

    # Build insert rows: one "main" image per product (sort_order=0)
    # If there are fewer images than products, images repeat using modulo
    rows = []
    for i, pid in enumerate(product_ids):
        main_img = image_urls[i % len(image_urls)]
        rows.append((pid, main_img, 0))

    # Bulk insert for speed and simplicity
    cur.executemany("""
        INSERT INTO product_images (product_id, image_url, sort_order)
        VALUES (?, ?, ?)
    """, rows)

    conn.commit()
    conn.close()
    print(f"Inserted {len(rows)} main images into product_images.")


if __name__ == "__main__":
    main()