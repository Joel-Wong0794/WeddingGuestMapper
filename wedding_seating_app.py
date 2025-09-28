import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import os

# --- 1. CONFIGURATION: TABLE COORDINATES ---
# CRITICAL: These are MOCK PIXEL COORDINATES based on a large sample image.
# You MUST open your 'floor_plan.png' in an image editor (like Paint or Preview)
# and adjust the (X, Y) pixel coordinates for each table to match your actual map.
# X is the horizontal position (from left), Y is the vertical position (from top).

TABLE_COORDS = {
    'VIP': (150, 250),
    '1': (800, 200),
    '2': (800, 500),
    '3': (500, 800),
    '4': (200, 750),
    '5': (300, 500),
    '6': (500, 250),
    '7': (650, 700),
    '8': (100, 500), # Added more mock tables based on typical size
    '9': (150, 600),
    '10': (250, 350),
    '11': (400, 150),
    '12': (700, 300),
    '13': (750, 650),
    '14': (450, 500),
    '15': (350, 650),
}
# Size of the circle to draw (adjust radius if needed)
CIRCLE_RADIUS = 35

# --- 2. DATA LOADING & IMAGE UTILITIES ---

@st.cache_data
def load_data(file_path, sheet_name):
    """Loads and cleans the guest data from the Excel file."""
    if not os.path.exists(file_path):
        st.error(f"Error: Data file not found at '{file_path}'. Please ensure the file is in the same directory.")
        return pd.DataFrame() # Return empty DataFrame on error

    try:
        # Load data from the specified Excel sheet
        df = pd.read_excel(file_path, sheet_name)
        # Standardize column names for easier searching (remove potential leading/trailing spaces)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading guest data: {e}")
        # Hint to the user if they might be missing the required library
        if 'No such file or directory' not in str(e) and 'xlrd' not in str(e) and 'openpyxl' not in str(e):
             st.warning("You might need to install 'openpyxl' to read Excel files: `pip install openpyxl`")
        return pd.DataFrame()

@st.cache_resource
def load_map_image(file_path):
    """Loads the base map image."""
    if not os.path.exists(file_path):
        st.error(f"Error: Map image file not found at '{file_path}'.")
        return None
    try:
        return Image.open(file_path).convert("RGB")
    except Exception as e:
        st.error(f"Error loading map image: {e}")
        return None

@st.cache_data
def get_search_terms(df):
    """Creates a unique, sorted list of all possible search terms for autocomplete."""
    # Ensure columns exist before trying to access them
    # Collect all unique Placard Names (these are the primary search targets)
    names = df['Placard Name'].dropna().astype(str).str.strip().tolist()
    
    # Collect all unique Relationships (as secondary search targets)
    relationships = df.get('Relationship to Couple', pd.Series()).dropna().astype(str).str.strip().tolist() 
    
    # Combine, remove duplicates, and sort alphabetically
    all_terms = list(set([t for t in names + relationships if t]))
    return sorted(all_terms, key=str.lower)


# Load Data and Search Terms
DATA_FILE = "./data/map_seating_plan.xlsx" # Updated to new directory
SHEET_NAME = "NameList" # Specify the sheet name
MAP_FILE = "./data/floor_plan.png" # Updated to new directory

# Call load_data and load_map_image
guest_df = load_data(DATA_FILE, SHEET_NAME)
all_search_terms = get_search_terms(guest_df)
base_map = load_map_image(MAP_FILE) # This now calls the function defined above

# --- 3. UI SETUP ---

st.set_page_config(
    page_title="Wedding Seating Finder",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    .big-font {
        font-size:30px !important;
        font-weight: bold;
    }
    .stSuccess {
        background-color: #f0fff4; /* Light green background */
        border-left: 6px solid #48bb78; /* Green border */
        padding: 15px;
        border-radius: 8px;
        font-size: 1.2em;
        margin-bottom: 20px;
        color: #000000; /* Set text color to black for high contrast */
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🥂 Find Your Seat")
st.markdown("### Welcome to the Celebration! Please enter your name to find your table.")

# Ensure data is loaded before proceeding
if guest_df.empty:
    st.stop()

# --- 4. SEARCH INPUT with Autocomplete/Dropdown ---

# 4.1. Primary search input (Name or Relationship)
search_selection = st.selectbox(
    "Start typing your name or relationship to find your seat:",
    options=[''] + all_search_terms, # Add an empty string for the initial prompt
    index=0,
    placeholder="e.g., Jane Doe, Groom's Aunt, or VIP"
)

final_search_query = search_selection if search_selection else None


# --- 5. SEARCH LOGIC AND DISPLAY ---

final_match = pd.DataFrame() # DataFrame to hold the single identified guest

if final_search_query:
    query_lower = final_search_query.strip().lower()

    # 5.1. Initial Search: Find all rows that match the query (either as a Placard Name or a Group Name)
    match_is_name = guest_df['Placard Name'].str.strip().str.lower().eq(query_lower)
    
    # Check for the Relationship match, ensuring the column exists
    if 'Relationship to Couple' in guest_df.columns:
        match_is_relationship = guest_df['Relationship to Couple'].str.strip().str.lower().eq(query_lower)
        initial_matches = guest_df[match_is_name | match_is_relationship].copy()
    else:
        initial_matches = guest_df[match_is_name].copy()


    # --- Step 1: Handle Multiple Matches (Group Selection) ---
    if len(initial_matches) > 1:
        st.info(f"We found **{len(initial_matches)}** guests matching **'{final_search_query}'**. Please select your specific placard name:")
        
        # Create a unique identifier string that matches the selectbox option format
        # This is CRITICAL for correctly identifying guests with duplicate placard names.
        initial_matches['UniqueSelection'] = initial_matches.apply(
            lambda row: f"{row['Placard Name']} ({row['Relationship to Couple']})" if 'Relationship to Couple' in row else row['Placard Name'], axis=1
        )
        
        # Create options for the second selectbox using this unique string
        selection_options = initial_matches['UniqueSelection'].tolist()
        
        # Add an initial prompt option
        selection_options.insert(0, "")

        # New selection box for the individual guest
        individual_selection = st.selectbox(
            "Select your specific name:",
            options=selection_options,
            index=0
        )
        
        if individual_selection:
            # Filter using the ENTIRE selected string (UniqueSelection), which guarantees uniqueness
            # This directly solves the issue of duplicate placard names in a group.
            final_match = initial_matches[initial_matches['UniqueSelection'] == individual_selection].copy()
            
            # Clean up the temporary column after use
            if 'UniqueSelection' in final_match.columns:
                final_match = final_match.drop(columns=['UniqueSelection'])

    # --- Step 2: Handle Single Match (Individual Selection) ---
    elif len(initial_matches) == 1:
        # A specific Placard Name was selected directly, or only one person matched the relationship.
        final_match = initial_matches
        
    # --- Step 3: Handle No Match ---
    # final_match remains an empty DataFrame if len(initial_matches) is 0

# --- 5.2. Final Processing and Display ---
if not final_match.empty:
    
    found_table = str(final_match['Table'].iloc[0]).upper()
    found_name = final_match['Placard Name'].iloc[0]
    
    # Use 'Relationship to Couple' for the Group field
    group_name = final_match['Relationship to Couple'].iloc[0] if 'Relationship to Couple' in final_match.columns else "Relationship N/A"

    # Build the structured success message content
    success_content = f"""
    **Your Placard:** {found_name}<br>
    **Table:** <span style="font-size: 1.5em; font-weight: bold; color: #38a169;">{found_table}</span><br>
    **Group:** {group_name}
    """
    # Display success message within the styled div
    st.markdown(
        f'<div class="stSuccess">🎉<br>{success_content}<br>Enjoy the Luncheon!!</div>',
        unsafe_allow_html=True
    )

    # 5.3. Display Map with Marker
    if base_map and found_table in TABLE_COORDS:
        st.markdown("### Location on Map:")

        # Create a copy of the base map to draw on
        drawn_map = base_map.copy()
        draw = ImageDraw.Draw(drawn_map)

        # Get coordinates and draw the circle
        x, y = TABLE_COORDS[found_table]

        # Draw a thick red circle marker
        draw.ellipse(
            (x - CIRCLE_RADIUS, y - CIRCLE_RADIUS, x + CIRCLE_RADIUS, y + CIRCLE_RADIUS),
            outline='#FF0000', # Red color
            width=10
        )

        # Display the marked image
        st.image(drawn_map, caption="Your Table Location (Marked in Red)", use_container_width=True)

    elif base_map:
        st.warning(f"Your table, '{found_table}', was found, but its location is missing from the map configuration (`TABLE_COORDS`).")
        # Display the original map
        st.image(base_map, caption="Full Seating Map (Table Not Marked)", use_container_width=True)

# 5.4. Handle Final Error
elif final_search_query and final_match.empty and len(initial_matches) == 0:
    st.error("Guest name or relationship not found. Please try entering a different name or ask an usher for assistance.")

else:
    # Display the static map if no search is active
    if base_map:
        st.markdown("### Full Seating Plan")
        st.image(base_map, caption="Please search your name above to see your table marked.", use_container_width=True)
