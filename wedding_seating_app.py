import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import os
import base64
from io import BytesIO

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
    names = df['Placard Name'].dropna().astype(str).str.strip().tolist()
    relationships = df.get('Relationship to Couple', pd.Series()).dropna().astype(str).str.strip().tolist() 
    
    # Combine, remove duplicates, and sort alphabetically
    all_terms = list(set([t for t in names + relationships if t]))
    return sorted(all_terms, key=str.lower)

def get_image_as_base64(image_obj):
    """Converts a PIL Image object to a base64 string for embedding in HTML."""
    if image_obj is None:
        return None
    
    # Save the PIL Image to a bytes buffer
    buffered = BytesIO()
    image_obj.save(buffered, format="PNG")
    
    # Encode the bytes to base64
    return base64.b64encode(buffered.getvalue()).decode()


# Load Data and Search Terms
DATA_FILE = "./data/map_seating_plan.xlsx"
SHEET_NAME = "NameList"
MAP_FILE = "./data/floor_plan.png"

# Call load_data and load_map_image
guest_df = load_data(DATA_FILE, SHEET_NAME)
all_search_terms = get_search_terms(guest_df)
base_map = load_map_image(MAP_FILE)

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
    /* Style for the embedded table */
    .stSuccess table {
        width: 100%;
        margin-top: 5px;
        border-collapse: collapse;
    }
    .stSuccess td {
        padding: 4px 0;
        vertical-align: top;
    }
    .stSuccess td:first-child {
        font-weight: bold;
        width: 30%;
    }
    /* New CSS to enable scrolling for large content */
    .scrollable-map {
        overflow-x: auto; /* Enable horizontal scrolling */
        overflow-y: auto; /* Enable vertical scrolling */
        max-width: 100%; /* Limit container width to the column width */
        border: 1px solid #ddd; /* Optional: Add border for visual cue */
        border-radius: 8px;
    }
    /* Ensure the image inside the scrollable container does not shrink unnecessarily */
    .scrollable-map img {
        min-width: 100%; /* Ensure it takes full width if container allows */
        max-width: none; /* Allow image to exceed container size */
        height: auto;
        display: block;
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

    # Build the structured success message content using an HTML table
    success_content = f"""
    <table>
        <tr>
            <td>Your Placard</td>
            <td>{found_name}</td>
        </tr>
        <tr>
            <td>Table</td>
            <td><span style="font-size: 1.5em; font-weight: bold; color: #38a169;">{found_table}</span></td>
        </tr>
        <tr>
            <td>Group</td>
            <td>{group_name}</td>
        </tr>
    </table>
    """
    # Display success message within the styled div
    st.markdown(
        f'<div class="stSuccess">🎉<br>{success_content}<br>Enjoy the Luncheon!!</div>',
        unsafe_allow_html=True
    )

    # 5.3. Display Map with Marker (Scrollable version)
    if base_map and found_table in TABLE_COORDS:
        st.markdown("### Location on Map (Scroll to View All):")

        # 1. Create a copy of the base map to draw on
        drawn_map = base_map.copy()
        draw = ImageDraw.Draw(drawn_map)

        # 2. Get coordinates and draw the circle
        x, y = TABLE_COORDS[found_table]

        # Draw a thick red circle marker
        draw.ellipse(
            (x - CIRCLE_RADIUS, y - CIRCLE_RADIUS, x + CIRCLE_RADIUS, y + CIRCLE_RADIUS),
            outline='#FF0000', # Red color
            width=10
        )

        # 3. Convert the marked image to base64
        base64_image_data = get_image_as_base64(drawn_map)
        
        # 4. Use markdown to embed the image in a scrollable div
        if base64_image_data:
            st.markdown(f"""
            <div class="scrollable-map">
                <img src="data:image/png;base64,{base64_image_data}" alt="Seating Map with Table Marked">
            </div>
            """, unsafe_allow_html=True)

    elif base_map:
        st.warning(f"Your table, '{found_table}', was found, but its location is missing from the map configuration (`TABLE_COORDS`).")
        # Display the original map using the scrollable markdown method
        base64_image_data = get_image_as_base64(base_map)
        if base64_image_data:
             st.markdown(f"""
            <div class="scrollable-map">
                <img src="data:image/png;base64,{base64_image_data}" alt="Full Seating Map">
            </div>
            """, unsafe_allow_html=True)


    # --- 5.4. Handle Final Error ---
    # (Error handled implicitly when final_match is empty)
# 5.4. Handle Final Error
elif final_search_query and final_match.empty and len(initial_matches) == 0:
    st.error("Guest name or relationship not found. Please try entering a different name or ask an usher for assistance.")

else:
    # Display the static map if no search is active (Scrollable version)
    if base_map:
        st.markdown("### Full Seating Plan (Scroll to View All)")
        base64_image_data = get_image_as_base64(base_map)
        if base64_image_data:
             st.markdown(f"""
            <div class="scrollable-map">
                <img src="data:image/png;base64,{base64_image_data}" alt="Full Seating Map">
            </div>
            """, unsafe_allow_html=True)
