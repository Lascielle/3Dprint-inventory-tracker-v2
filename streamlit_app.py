from pathlib import Path
import sqlite3
import streamlit as st
import altair as alt
import pandas as pd

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title="Inventory tracker",
    page_icon=":shopping_bags:",  # This is an emoji shortcode. Could be a URL too.
)

# -----------------------------------------------------------------------------
# Declare some useful functions.


def connect_db():
    """Connects to the sqlite database."""
    DB_FILENAME = Path(__file__).parent / "inventory.db"
    db_already_exists = DB_FILENAME.exists()

    conn = sqlite3.connect(DB_FILENAME)
    db_was_just_created = not db_already_exists

    return conn, db_was_just_created


def initialize_data(conn):
    """Initializes the inventory table with some data."""
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            price REAL,
            units_sold INTEGER,
            units_left INTEGER,
            cost_price REAL,
            reorder_point INTEGER,
            description TEXT
        )
        """
    )

    # Insert initial data into the inventory table if it's newly created
    cursor.execute(
        """
        INSERT INTO inventory
            (item_name, price, units_sold, units_left, cost_price, reorder_point, description)
        VALUES
            ('Bottled Water (500ml)', 1.50, 115, 15, 0.80, 16, 'Hydrating bottled water'),
            ('Soda (355ml)', 2.00, 93, 8, 1.20, 10, 'Carbonated soft drink'),
            ('Energy Drink (250ml)', 2.50, 12, 18, 1.50, 8, 'High-caffeine energy drink'),
            ('Coffee (hot, large)', 2.75, 11, 14, 1.80, 5, 'Freshly brewed hot coffee'),
            ('Juice (200ml)', 2.25, 11, 9, 1.30, 5, 'Fruit juice blend')
        """
    )

    conn.commit()


def load_data(conn):
    """Loads the inventory data from the database."""
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM inventory")
    data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=[
            "id",
            "item_name",
            "price",
            "units_sold",
            "units_left",
            "cost_price",
            "reorder_point",
            "description",
        ],
    )
    return df


def update_inventory(conn, sku_id, quantity, action):
    """Updates the inventory by adding or removing stock."""
    cursor = conn.cursor()

    if action == "add":
        cursor.execute("UPDATE inventory SET units_left = units_left + ? WHERE id = ?", (quantity, sku_id))
    elif action == "remove":
        cursor.execute("UPDATE inventory SET units_left = units_left - ? WHERE id = ?", (quantity, sku_id))

    conn.commit()


# -----------------------------------------------------------------------------
# Build the app

# Set the title that appears at the top of the page.
st.title(":shopping_bags: Inventory Tracker")

# Connect to database and create table if needed
conn, db_was_just_created = connect_db()

# Initialize data if the database was just created
if db_was_just_created:
    initialize_data(conn)
    st.toast("Database initialized with some sample data.")

# Load and display inventory
st.subheader("Current Inventory")
df = load_data(conn)
st.table(df)

# Transaction Section
st.subheader("Transact Inventory")

# Dropdown to select SKU (with both ID and item_name)
sku_options = {row["id"]: f"{row['id']} - {row['item_name']}" for i, row in df.iterrows()}
selected_sku_id = st.selectbox("Select SKU", options=list(sku_options.keys()), format_func=lambda x: sku_options[x])

quantity = st.number_input("Quantity", min_value=1, step=1)

col1, col2 = st.columns(2)

with col1:
    if st.button("Receive Inventory"):
        update_inventory(conn, selected_sku_id, quantity, "add")
        st.success(f"Added {quantity} units to SKU {selected_sku_id}")

with col2:
    if st.button("Remove Inventory"):
        update_inventory(conn, selected_sku_id, quantity, "remove")
        st.warning(f"Removed {quantity} units from SKU {selected_sku_id}")

# -----------------------------------------------------------------------------
# Charts Section

st.subheader("Inventory Status")

# Add a bar chart for units left and reorder points
if df is not None:
    need_to_reorder = df[df["units_left"] < df["reorder_point"]].loc[:, "item_name"]
    if len(need_to_reorder) > 0:
        items = "\n".join(f"* {name}" for name in need_to_reorder)
        st.error(f"Reorder needed for:\n {items}")

    st.altair_chart(
        alt.Chart(df)
        .mark_bar()
        .encode(x="units_left", y="item_name"),
        use_container_width=True,
    )
