import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import os
import base64
from io import BytesIO

# --- 1. CONFIGURATION: TABLE COORDINATES & DIMENSIONS ---
# CRITICAL: These are MOCK PIXEL COORDINATES based on the ORIGINAL size of your map.
# The application will automatically scale these coordinates if the map is resized below.

TABLE_COORDS = {
    'VIP': (6250, 1820),
    '1': (7200, 1820),
    '2': (5065, 1820),
    '3': (4115, 2000),
    '4': (3650, 4100),
    '5': (2705, 4100),
    '6': (1750, 4100),
    '7': (800, 4100)
}
# Size of the circle to draw (adjust radius if needed)
CIRCLE_RADIUS = 35

# NEW: Maximum width for the map image. Image will be scaled down if it exceeds this.
MAX_MAP_WIDTH_PIXELS = 1800 

# NEW: File path for the static overview image
OVERVIEW_MAP_FILE = "./data/official_seating_overview.png"

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
    """Loads the base map image and resizes it if too large.
       Returns the image object and the scaling factor applied (1.0 if no resizing occurred)."""
    if not os.path.exists(file_path):
        st.error(f"Error: Map image file not found at '{file_path}'.")
        return None, 1.0
    try:
        image = Image.open(file_path).convert("RGB")
        original_width, original_height = image.size
        
        # Determine if resizing is necessary
        if original_width > MAX_MAP_WIDTH_PIXELS:
            # Calculate the new height to maintain aspect ratio
            scaling_factor = MAX_MAP_WIDTH_PIXELS / original_width
            new_height = int(original_height * scaling_factor)
            
            # Resize the image using the high-quality resampling filter
            resized_image = image.resize((MAX_MAP_WIDTH_PIXELS, new_height), Image.Resampling.LANCZOS)
            
            # Return the resized image and the scaling factor
            return resized_image, scaling_factor
        
        # If no resizing needed, scaling factor is 1.0
        return image, 1.0
        
    except Exception as e:
        st.error(f"Error loading map image: {e}")
        return None, 1.0

@st.cache_resource
def load_overview_image(file_path):
    """Loads the static overview map image and resizes it if too large."""
    if not os.path.exists(file_path):
        st.warning(f"Warning: Overview map file not found at '{file_path}'.")
        return None
    try:
        image = Image.open(file_path).convert("RGB")
        original_width, original_height = image.size
        
        # Determine if resizing is necessary using the same MAX_MAP_WIDTH_PIXELS
        if original_width > MAX_MAP_WIDTH_PIXELS:
            scaling_factor = MAX_MAP_WIDTH_PIXELS / original_width
            new_height = int(original_height * scaling_factor)
            
            # Resize the image
            resized_image = image.resize((MAX_MAP_WIDTH_PIXELS, new_height), Image.Resampling.LANCZOS)
            return resized_image
        
        return image
        
    except Exception as e:
        st.error(f"Error loading overview map image: {e}")
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
    # Use JPEG format for the overview image to keep size down, but PNG for the detailed/marked map
    format = "JPEG" if image_obj.format == "JPEG" else "PNG"
    image_obj.save(buffered, format=format)
    
    # Encode the bytes to base64
    return base64.b64encode(buffered.getvalue()).decode()


# Load Data and Search Terms
DATA_FILE = "./data/map_seating_plan.xlsx"
SHEET_NAME = "NameList"
MAP_FILE = "./data/floor_plan.png"

# Call load_data and load_map_image
guest_df = load_data(DATA_FILE, SHEET_NAME)

# Load the main map (which returns the scale factor)
base_map_and_scale = load_map_image(MAP_FILE)
base_map = base_map_and_scale[0]
MAP_SCALE_FACTOR = base_map_and_scale[1] # Store the scale factor

# Load the overview map
overview_map = load_overview_image(OVERVIEW_MAP_FILE)

all_search_terms = get_search_terms(guest_df)


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
        max-height: 1400px; /* NEW: Set max height for the detailed map container */
        width: 100%; /* Stretch to 100% of the column width */
        border: 1px solid #ddd; /* Optional: Add border for visual cue */
        border-radius: 8px;
        margin-top: 15px;
    }
    /* Ensure the image inside the scrollable container adapts its width */
    .scrollable-map img {
        min-width: 100%; 
        width: auto; /* Allow image to use its natural width (up to MAX_MAP_WIDTH_PIXELS) */
        max-width: none; /* Crucial: Allows scrolling if the image width > container width */
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
    "*Start typing your name or relationship to Bride/Groom:*",
    options=[''] + all_search_terms, # Add an empty string for the initial prompt
    index=0,
    placeholder="e.g., Bride's Aunt, Groom's Family, Uncle, Friend"
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
            "*Select your specific name:*",
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
        f'<div class="stSuccess">🎉 Here Is Your Info:<br>{success_content}<br>👰🏻🤵🏻Enjoy our Wedding Luncheon!!</div>',
        unsafe_allow_html=True
    )

    # NEW: Display the Overview Map (placed here, after info table and before detailed map)
    if overview_map:
        st.markdown("### General Seating Overview")
        st.image(overview_map, width='stretch')


    # 5.3. Display Map with Marker (Scrollable version)
    if base_map and found_table in TABLE_COORDS:
        st.markdown("### Floor Plan (Scroll to View More)")
        st.markdown("*Red Dot Indicates Your Table.*")
        # 1. Create a copy of the base map to draw on
        drawn_map = base_map.copy()
        draw = ImageDraw.Draw(drawn_map)

        # 2. Get coordinates and apply scaling factor
        original_x, original_y = TABLE_COORDS[found_table]
        
        # Scale coordinates based on image resizing
        x = int(original_x * MAP_SCALE_FACTOR)
        y = int(original_y * MAP_SCALE_FACTOR)
        
        # The circle radius should also scale to remain proportional
        scaled_radius = int(CIRCLE_RADIUS * MAP_SCALE_FACTOR)

        # Draw a thick red circle marker
        draw.ellipse(
            (x - scaled_radius, y - scaled_radius, x + scaled_radius, y + scaled_radius),
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
    
    # NEW: Display Overview Map here for failed searches
    if overview_map:
        st.markdown("### General Seating Overview")
        st.image(overview_map, width='stretch')

    # Display the static map if search fails (Scrollable version)
    if base_map:
        st.markdown("### Floor Plan (Scroll to View More)")
        st.markdown("*Red Dot Indicates Your Table.*")
        base64_image_data = get_image_as_base64(base_map)
        if base64_image_data:
             st.markdown(f"""
            <div class="scrollable-map">
                <img src="data:image/png;base64,{base64_image_data}" alt="Full Seating Map">
            </div>
            """, unsafe_allow_html=True)

else:
    # Display the static map if no search is active (Initial load)
    
    # NEW: Display Overview Map first for initial load
    if overview_map:
        st.markdown("### General Seating Overview")
        st.image(overview_map, width='stretch')
        
    if base_map:
        st.markdown("### Floor Plan (Scroll to View More)")
        st.markdown("*Red Dot Indicates Your Table.*")
        base64_image_data = get_image_as_base64(base_map)
        if base64_image_data:
             st.markdown(f"""
            <div class="scrollable-map">
                <img src="data:image/png;base64,{base64_image_data}" alt="Full Seating Map">
            </div>
            """, unsafe_allow_html=True)
