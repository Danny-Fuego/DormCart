import sqlite3
from pathlib import Path

# Resolve the SQLite database path relative to this file
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "dormcart.db"


def table_exists(cur, name: str) -> bool:
    """Return True if a table exists in the current SQLite database."""
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,)
    ).fetchone()
    return row is not None


def col_exists(cur, table: str, col: str) -> bool:
    """Return True if a column exists in a given SQLite table."""
    # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table});").fetchall()]
    return col in cols


def flag_done(cur, name: str) -> bool:
    """
    Seed flags let this script be re-run safely without duplicating seed data.
    If the flag exists, that seed step has already been applied.
    """
    row = cur.execute("SELECT 1 FROM seed_flags WHERE name = ?", (name,)).fetchone()
    return row is not None


def set_flag(cur, name: str):
    """Mark a seed step as completed."""
    cur.execute("INSERT OR IGNORE INTO seed_flags (name) VALUES (?)", (name,))


def main():
    # Connect to SQLite and enable Row access (helps if you inspect results during debugging)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Enforce foreign key constraints (SQLite requires this PRAGMA per connection)
    cur.execute("PRAGMA foreign_keys = ON;")

    # Tracks one-time seed/migration steps to avoid re-inserting on every run
    cur.execute("""
    CREATE TABLE IF NOT EXISTS seed_flags (
        name TEXT PRIMARY KEY
    );
    """)

    # Basic user table used for authentication and profile display
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        hash TEXT NOT NULL,
        first_name TEXT,
        last_name TEXT,
        display_name TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Core product table; seller_id references users (SET NULL if seller is deleted)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        condition TEXT,
        color TEXT,
        category TEXT,
        seller_id INTEGER,
        is_sold INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)

    # Supports multiple images per product (first image by sort_order becomes thumbnail)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS product_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        image_url TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    );
    """)

    # Cart items (composite primary key: one row per user per product)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cart_items (
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, product_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    );
    """)

    # Rating table is database-ready even if the UI doesn’t fully implement rating yet
    cur.execute("""
    CREATE TABLE IF NOT EXISTS seller_ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER NOT NULL,
        rater_id INTEGER NOT NULL,
        product_id INTEGER,
        rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
        comment TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (rater_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL,
        UNIQUE (seller_id, rater_id, product_id)
    );
    """)

    # --------------------- Lightweight "migrations" ---------------------
    # SQLite has limited ALTER TABLE support, so this approach checks for missing columns
    # and adds them when needed. This allows the schema to evolve without dropping tables.
    #
    # (ChatGPT helped me understand SQLite ALTER TABLE limitations and how to safely
    # apply incremental changes like this.)
    if not col_exists(cur, "users", "first_name"):
        cur.execute("ALTER TABLE users ADD COLUMN first_name TEXT;")
        print("Added users.first_name")

    if not col_exists(cur, "users", "last_name"):
        cur.execute("ALTER TABLE users ADD COLUMN last_name TEXT;")
        print("Added users.last_name")

    if not col_exists(cur, "users", "display_name"):
        cur.execute("ALTER TABLE users ADD COLUMN display_name TEXT;")
        print("Added users.display_name")

    if not col_exists(cur, "users", "created_at"):
        # Existing rows won't automatically get a default when adding the column,
        # so this script backfills values after adding it.
        cur.execute("ALTER TABLE users ADD COLUMN created_at TEXT;")
        cur.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL;")
        print("Added users.created_at (no default) + backfilled")

    if not col_exists(cur, "products", "category"):
        cur.execute("ALTER TABLE products ADD COLUMN category TEXT;")
        print("Added products.category")

    # --------------------- Seed data (safe to re-run) ---------------------

    # Seed a single demo user (id=1) that owns seeded products
    seed_user_flag = "seed_user1_v1"
    if not flag_done(cur, seed_user_flag):
        existing_user1 = cur.execute("SELECT id FROM users WHERE id = 1;").fetchone()
        if not existing_user1:
            cur.execute("""
                INSERT INTO users (id, email, hash, first_name, last_name, display_name, created_at)
                VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, ("daniel@example.com", "seed_hash_not_for_login", "Daniel", "Baadom", "Daniel Baadom"))
            print("Created seed user id=1")
        set_flag(cur, seed_user_flag)
    else:
        print("seed user step already done, skipping")

    # Backfill the display name fields for user 1 if they were empty at any point
    backfill_name_flag = "backfill_user1_real_name_v1"
    if not flag_done(cur, backfill_name_flag):
        cur.execute("""
            UPDATE users
            SET
                first_name = COALESCE(NULLIF(first_name, ''), 'Daniel'),
                last_name = COALESCE(NULLIF(last_name, ''), 'Baadom'),
                display_name = COALESCE(NULLIF(display_name, ''), 'Daniel Baadom')
            WHERE id = 1
        """)
        set_flag(cur, backfill_name_flag)
        print("Backfilled user 1 real name (first run only).")
    else:
        print("user 1 backfill already done, skipping")

    # Seed product catalog (one-time)
    products_seed_flag = "products_seed_v3_unique_120"
    if not flag_done(cur, products_seed_flag):
        seller_id = 1

        # Seed inventory used to populate the homepage, category pages, and best-deals sections
        products = [
            ("Dorm Desk Lamp", "Bright LED lamp for late-night study", 12.00, "Good", "Black", "Dorm & Room", seller_id),
            ("Memory Foam Pillow", "Comfort pillow, clean and fresh", 14.50, "Like New", "White", "Dorm & Room", seller_id),
            ("Twin XL Sheet Set", "Soft sheets for dorm bed", 18.00, "Good", "Gray", "Dorm & Room", seller_id),
            ("Laundry Hamper", "Tall hamper, sturdy handles", 10.00, "Good", "Black", "Dorm & Room", seller_id),
            ("Over-the-Door Hooks", "Hooks for towels, bags, coats", 6.00, "New", "Silver", "Dorm & Room", seller_id),
            ("Closet Hangers Pack", "Pack of hangers, strong grip", 7.00, "New", "Black", "Dorm & Room", seller_id),
            ("Bedside Caddy", "Pocket organizer for bed frame", 9.00, "Like New", "Black", "Dorm & Room", seller_id),
            ("Desk Organizer Tray", "Keeps pens and small items tidy", 8.00, "Good", "Black", "Dorm & Room", seller_id),
            ("Whiteboard Calendar", "Monthly planner board + marker", 11.00, "Good", "White", "Dorm & Room", seller_id),
            ("Dry Erase Marker Set", "Assorted markers (set)", 5.00, "New", "Mixed", "Dorm & Room", seller_id),
            ("Throw Blanket", "Cozy blanket for cold nights", 13.00, "Good", "Blue", "Dorm & Room", seller_id),
            ("Area Rug Small", "Soft rug for dorm floor", 20.00, "Fair", "Gray", "Dorm & Room", seller_id),
            ("Shower Curtain", "Simple curtain for shared bathroom", 9.50, "Good", "White", "Dorm & Room", seller_id),
            ("Shower Mat", "Non-slip mat for bathroom", 8.50, "Good", "Black", "Dorm & Room", seller_id),
            ("Storage Bin Large", "Plastic bin with lid", 12.50, "Good", "Clear", "Dorm & Room", seller_id),
            ("Underbed Storage Bag", "Zipper bag for clothes", 11.00, "Like New", "Black", "Dorm & Room", seller_id),
            ("Command Strip Pack", "Wall-safe strips (pack)", 6.50, "New", "Mixed", "Dorm & Room", seller_id),
            ("Clip-On Fan", "Quiet fan for dorm bed/desk", 15.00, "Good", "White", "Dorm & Room", seller_id),
            ("Alarm Clock", "Simple alarm clock, loud ring", 8.00, "Good", "Black", "Dorm & Room", seller_id),
            ("Desk Chair Cushion", "Extra comfort for long sessions", 10.00, "Good", "Black", "Dorm & Room", seller_id),

            ("Wireless Earbuds", "Clear sound, good battery", 25.00, "Good", "Black", "Electronics", seller_id),
            ("Bluetooth Speaker", "Portable speaker, strong bass", 22.00, "Good", "Black", "Electronics", seller_id),
            ("Power Bank 10000mAh", "Portable charger, reliable", 18.00, "Good", "Black", "Electronics", seller_id),
            ("Power Bank 20000mAh", "Large capacity, fast charge", 28.00, "Good", "Black", "Electronics", seller_id),
            ("USB-C Fast Charger", "Wall charger, fast charging", 12.00, "Like New", "White", "Electronics", seller_id),
            ("USB-C Cable 6ft", "Long cable, durable", 7.00, "New", "Black", "Electronics", seller_id),
            ("Lightning Cable", "iPhone cable, working", 6.00, "Good", "White", "Electronics", seller_id),
            ("HDMI Cable 6ft", "HDMI cable for monitor/TV", 7.00, "New", "Black", "Electronics", seller_id),
            ("Wireless Mouse", "Smooth mouse, no lag", 12.00, "Good", "Black", "Electronics", seller_id),
            ("Mechanical Keyboard", "Clicky keys, great feel", 45.00, "Like New", "Black", "Electronics", seller_id),
            ("Compact Keyboard", "Small keyboard for dorm desk", 18.00, "Good", "Black", "Electronics", seller_id),
            ("Laptop Stand", "Adjustable stand, better posture", 17.00, "Like New", "Silver", "Electronics", seller_id),
            ("Phone Stand", "Adjustable phone holder", 7.00, "New", "Silver", "Electronics", seller_id),
            ("Webcam 1080p", "Good for zoom classes", 28.00, "Good", "Black", "Electronics", seller_id),
            ("Ring Light Small", "Desk ring light, bright", 14.00, "Good", "White", "Electronics", seller_id),
            ("Headphone Stand", "Stand for headphones", 9.00, "Good", "Black", "Electronics", seller_id),
            ("Screen Cleaning Kit", "Spray + cloth set", 5.00, "New", "Mixed", "Electronics", seller_id),
            ("Flash Drive 64GB", "USB drive, fast read/write", 12.00, "New", "Silver", "Electronics", seller_id),
            ("Ethernet Cable", "Reliable LAN cable", 6.00, "New", "Black", "Electronics", seller_id),
            ("Travel Adapter", "Multi-plug adapter", 9.00, "Good", "Black", "Electronics", seller_id),

            ("Calculus Textbook", "Good for Calc I/II", 35.00, "Good", "Mixed", "Books", seller_id),
            ("Physics Textbook", "Intro physics textbook", 32.00, "Good", "Mixed", "Books", seller_id),
            ("Chemistry Textbook", "Chem book, solid condition", 30.00, "Good", "Mixed", "Books", seller_id),
            ("English Composition Reader", "Reader for writing class", 18.00, "Good", "Mixed", "Books", seller_id),
            ("Programming Handbook", "Beginner-friendly coding guide", 20.00, "Like New", "Mixed", "Books", seller_id),
            ("Discrete Math Notes Binder", "Organized notes + practice", 12.00, "Good", "Mixed", "Books", seller_id),
            ("Lab Manual", "Lab manual, minimal writing", 9.00, "Good", "Mixed", "Books", seller_id),
            ("Exam Prep Book", "Practice questions included", 15.00, "Good", "Mixed", "Books", seller_id),
            ("Notebook Bundle", "Pack of 6 notebooks", 9.00, "New", "Mixed", "Books", seller_id),
            ("Graph Paper Pad", "Graph pad for math", 6.50, "New", "Mixed", "Books", seller_id),
            ("Highlighter Set", "Set of highlighters", 5.00, "New", "Mixed", "Books", seller_id),
            ("Sticky Notes Pack", "Sticky notes (multi colors)", 4.50, "New", "Mixed", "Books", seller_id),
            ("Binder + Dividers", "Binder with labeled tabs", 8.00, "Good", "Mixed", "Books", seller_id),
            ("Index Cards Pack", "100 count index cards", 4.00, "New", "Mixed", "Books", seller_id),
            ("Dictionary", "Handy desk dictionary", 7.00, "Good", "Mixed", "Books", seller_id),
            ("Iliad Copy", "Paperback copy of The Iliad", 10.00, "Good", "Mixed", "Books", seller_id),
            ("Greek Mythology Book", "Stories of Greek myths", 11.00, "Good", "Mixed", "Books", seller_id),
            ("Novel Bundle", "Set of 3 novels", 12.00, "Good", "Mixed", "Books", seller_id),
            ("Study Planner", "Planner to track assignments", 6.00, "New", "Mixed", "Books", seller_id),
            ("TI-84 Manual", "Guidebook for TI-84", 5.00, "Good", "Mixed", "Books", seller_id),

            ("Black Hoodie", "Warm hoodie, clean", 18.00, "Good", "Black", "Clothing", seller_id),
            ("Blue Hoodie", "Comfort hoodie, no tears", 16.00, "Good", "Blue", "Clothing", seller_id),
            ("Cargo Pants", "Comfort fit cargo pants", 22.00, "Good", "Black", "Clothing", seller_id),
            ("Jeans", "Good jeans, fits well", 20.00, "Good", "Blue", "Clothing", seller_id),
            ("Sweatpants", "Soft sweatpants for dorm", 16.00, "Good", "Gray", "Clothing", seller_id),
            ("Jacket", "Light jacket, great condition", 30.00, "Like New", "Black", "Clothing", seller_id),
            ("T-Shirt Pack", "Pack of 3 tees", 12.00, "Good", "Mixed", "Clothing", seller_id),
            ("Socks Pack", "Pack of socks", 7.00, "New", "Mixed", "Clothing", seller_id),
            ("Cap", "Simple cap", 8.00, "Good", "Black", "Clothing", seller_id),
            ("Belt", "Everyday belt", 9.00, "Good", "Black", "Clothing", seller_id),
            ("Gym Shorts", "Athletic shorts", 10.00, "Good", "Black", "Clothing", seller_id),
            ("Workout Tee", "Breathable shirt", 9.50, "Good", "Gray", "Clothing", seller_id),
            ("Dress Shirt", "Button-up shirt", 14.00, "Good", "White", "Clothing", seller_id),
            ("Tie", "Formal tie", 6.00, "Good", "Black", "Clothing", seller_id),
            ("Winter Gloves", "Warm gloves", 8.50, "Good", "Black", "Clothing", seller_id),
            ("Beanie", "Warm beanie", 7.50, "Good", "Black", "Clothing", seller_id),
            ("Sneakers", "Everyday sneakers", 35.00, "Good", "White", "Clothing", seller_id),
            ("Slides", "Comfy slides", 12.00, "Good", "Black", "Clothing", seller_id),
            ("Rain Jacket", "Light rain jacket", 20.00, "Good", "Blue", "Clothing", seller_id),
            ("Laundry Bag", "Clothes bag for washer", 6.00, "Good", "Black", "Clothing", seller_id),

            ("Electric Kettle", "Boils fast, clean inside", 18.00, "Good", "Black", "Kitchen", seller_id),
            ("Mug Set", "Set of 2 mugs", 9.00, "Good", "Mixed", "Kitchen", seller_id),
            ("Plate Set", "2 plates + 2 bowls", 12.00, "Good", "Mixed", "Kitchen", seller_id),
            ("Cutlery Set", "Forks/spoons/knives", 10.00, "Good", "Silver", "Kitchen", seller_id),
            ("Food Containers", "Meal prep containers", 11.00, "Good", "Clear", "Kitchen", seller_id),
            ("Water Bottle", "Reusable bottle", 7.00, "Good", "Black", "Kitchen", seller_id),
            ("Coffee Maker", "Small coffee maker", 25.00, "Good", "Black", "Kitchen", seller_id),
            ("Mini Blender", "Smoothies in dorm", 22.00, "Good", "Silver", "Kitchen", seller_id),
            ("Cutting Board", "Durable cutting board", 6.50, "Good", "Brown", "Kitchen", seller_id),
            ("Dish Rack", "Drying rack for dishes", 13.00, "Good", "Black", "Kitchen", seller_id),
            ("Dish Soap Bundle", "Soap + sponge set", 5.00, "New", "Mixed", "Kitchen", seller_id),
            ("Sponge Pack", "Pack of sponges", 4.00, "New", "Mixed", "Kitchen", seller_id),
            ("Microwave Cover", "Cover for microwave heating", 5.50, "Good", "Mixed", "Kitchen", seller_id),
            ("Lunch Box", "Insulated lunch box", 12.00, "Good", "Black", "Kitchen", seller_id),
            ("Thermos", "Keeps drinks hot/cold", 14.00, "Good", "Black", "Kitchen", seller_id),
            ("Snack Bowl Set", "Small bowls (set)", 8.00, "Good", "Mixed", "Kitchen", seller_id),
            ("Measuring Cup Set", "Measuring cups set", 6.00, "Good", "Mixed", "Kitchen", seller_id),
            ("Can Opener", "Works smoothly", 5.00, "Good", "Black", "Kitchen", seller_id),
            ("Pan", "Nonstick pan", 14.00, "Good", "Black", "Kitchen", seller_id),
            ("Pot", "Medium pot, good condition", 16.00, "Good", "Silver", "Kitchen", seller_id),

            ("Bike Helmet", "Safe helmet, adjustable", 20.00, "Good", "Black", "Transport", seller_id),
            ("Bike Lock", "Strong lock", 12.00, "Good", "Black", "Transport", seller_id),
            ("LED Bike Light", "Front light + rear light", 11.00, "Good", "Black", "Transport", seller_id),
            ("Reflective Vest", "High visibility vest", 8.00, "New", "Yellow", "Transport", seller_id),
            ("Tire Pump", "Portable pump", 10.00, "Good", "Black", "Transport", seller_id),
            ("Skateboard", "Smooth wheels, good deck", 35.00, "Good", "Black", "Transport", seller_id),
            ("Scooter", "Foldable scooter", 45.00, "Good", "Black", "Transport", seller_id),
            ("Car Phone Mount", "Dashboard mount", 9.00, "Good", "Black", "Transport", seller_id),
            ("Car Charger", "Dual USB car charger", 7.00, "Good", "Black", "Transport", seller_id),
            ("Travel Duffel Bag", "Weekend bag", 18.00, "Good", "Black", "Transport", seller_id),
            ("Backpack Rain Cover", "Rain cover for backpack", 7.00, "Good", "Black", "Transport", seller_id),
            ("Umbrella", "Compact umbrella", 8.50, "Good", "Black", "Transport", seller_id),
            ("Transit Card Holder", "Card holder wallet", 5.00, "Good", "Black", "Transport", seller_id),
            ("Seat Cushion", "Cushion for long rides", 10.00, "Good", "Gray", "Transport", seller_id),
            ("Handlebar Phone Holder", "Bike phone holder", 11.50, "Good", "Black", "Transport", seller_id),
            ("Helmet Lock", "Small helmet lock", 6.50, "Good", "Black", "Transport", seller_id),
            ("Bike Bell", "Loud bell", 5.00, "New", "Black", "Transport", seller_id),
            ("Bike Reflector Set", "Reflectors set", 6.00, "New", "Mixed", "Transport", seller_id),
            ("Mini First Aid Kit", "Small kit for travel", 9.00, "New", "Red", "Transport", seller_id),
            ("Portable Tool Kit", "Small tool kit for quick fixes", 12.00, "Good", "Black", "Transport", seller_id),
        ]

        print(f"Seeding {len(products)} products (one-time)...")

        # Bulk insert is faster and avoids repetitive execute() calls
        cur.executemany("""
            INSERT INTO products (title, description, price, condition, color, category, seller_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, products)

        set_flag(cur, products_seed_flag)
        print("Products seeded.")
    else:
        print("Products already seeded, skipping.")

    conn.commit()
    conn.close()
    print("Database initialized / updated successfully.")


if __name__ == "__main__":
    main()