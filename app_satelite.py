import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ---------------------------------------------------------
# 1. Page Configuration
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="NASA Night Lights Viewer")

st.title("🌃 NASA Nighttime Lights & Unique Stations")
st.markdown("""
* **Objective:** Visual inspection of urbanization around water quality sampling stations.
* **Stations:** Displays **UNIQUE (Distinct)** locations based on Latitude/Longitude.
* **Color Coding:**
    * <span style='color:blue'>**● Blue:**</span> Training Set
    * <span style='color:red'>**● Red:**</span> Validation Set
* **Background:** Toggle between NASA **2012 (City Lights)** and **2016 (Black Marble)**.
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Data Loading (DISTINCT LOCATIONS WITH SOURCE)
# ---------------------------------------------------------
@st.cache_data
def load_unique_data():
    files = {
        'Training Set': 'TRAINING_SET.csv',
        'Validation Set': 'VALIDATION_SET.csv'
    }
    combined_df = pd.DataFrame()
    
    for source, f in files.items():
        try:
            df = pd.read_csv(f)
            # Check if coordinates exist
            if {'Latitude', 'Longitude'}.issubset(df.columns):
                # Keep coordinates and add source info
                temp = df[['Latitude', 'Longitude']].copy()
                temp['Source'] = source
                combined_df = pd.concat([combined_df, temp], ignore_index=True)
        except Exception:
            continue
            
    # [CRITICAL] Drop duplicates to keep only distinct physical locations
    # We keep the first occurrence, which is fine for distinct locations.
    unique_df = combined_df.drop_duplicates(subset=['Latitude', 'Longitude']).reset_index(drop=True)
    
    return unique_df

df = load_unique_data()

if df.empty:
    st.error("Error: CSV files not found. Please check 'TRAINING_SET.csv' and 'VALIDATION_SET.csv'.")
    st.stop()

# ---------------------------------------------------------
# 3. Sidebar Settings (English)
# ---------------------------------------------------------
st.sidebar.header("🛠️ Map Settings")

# Background Map Selection
st.sidebar.subheader("🌍 NASA Satellite Version")
nasa_version = st.sidebar.radio(
    "Select Background Map:",
    ["2012 City Lights (Brighter)", "2016 Black Marble (Refined)"],
    index=1 # Default to 2016
)

st.sidebar.markdown("---")

# Radius Settings
st.sidebar.subheader("⭕ Buffer Radius")
show_1km = st.sidebar.checkbox("1km", value=True)
show_3km = st.sidebar.checkbox("3km", value=True)
show_5km = st.sidebar.checkbox("5km", value=True)
show_10km = st.sidebar.checkbox("10km", value=True)

# Performance Control
st.sidebar.markdown("---")
total_unique = len(df)
st.sidebar.caption(f"Unique Locations: {total_unique}")

# Slider just in case there are too many unique points
max_points = st.sidebar.slider(
    "Max Stations to Display", 
    min_value=10, 
    max_value=total_unique, 
    value=min(100, total_unique),
    step=10
)

# ---------------------------------------------------------
# 4. Map Generation
# ---------------------------------------------------------
# Sampling if necessary
if len(df) > max_points:
    display_df = df.sample(n=max_points, random_state=42)
    st.toast(f"Displaying {max_points} random stations out of {total_unique}.", icon="ℹ️")
else:
    display_df = df

# Center map
center_lat = display_df['Latitude'].mean()
center_lon = display_df['Longitude'].mean()

m = folium.Map(location=[center_lat, center_lon], zoom_start=8, tiles=None)

# Set Tile Layer
if "2012" in nasa_version:
    tile_url = 'https://map1.vis.earthdata.nasa.gov/wmts-webmerc/VIIRS_CityLights_2012/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg'
    attr_txt = 'NASA GIBS 2012 City Lights'
else:
    # 2016 Black Marble
    tile_url = 'https://map1.vis.earthdata.nasa.gov/wmts-webmerc/VIIRS_Black_Marble/default/2016-01-01/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png'
    attr_txt = 'NASA GIBS 2016 Black Marble'

folium.TileLayer(
    tiles=tile_url,
    attr=attr_txt,
    name=nasa_version,
    overlay=False,
    control=True
).add_to(m)

# ---------------------------------------------------------
# 5. Draw Markers & Buffers
# ---------------------------------------------------------
for idx, row in display_df.iterrows():
    lat, lon = row['Latitude'], row['Longitude']
    source = row['Source']
    
    # Determine color based on source
    if source == 'Training Set':
        marker_color = 'blue'
    else:
        marker_color = 'red'
    
    # 1. Center Point (Colored based on source, size reduced by half)
    folium.CircleMarker(
        location=[lat, lon],
        radius=1.5,         # Reduced radius by half (from 3 to 1.5)
        color=marker_color,
        fill=True,
        fill_color=marker_color,
        popup=f"Lat: {lat:.4f}, Lon: {lon:.4f}<br>Source: {source}"
    ).add_to(m)
    
    # 2. Radius Circles (Cyan Outline - No Fill)
    radii = []
    if show_1km: radii.append(1)
    if show_3km: radii.append(3)
    if show_5km: radii.append(5)
    if show_10km: radii.append(10)
    
    for km in radii:
        folium.Circle(
            location=[lat, lon],
            radius=km * 1000,   # Meters
            color='cyan',       # Cyan is best for dark maps
            weight=1,           # Thin line
            fill=False,         # IMPORTANT: No fill to see the lights
            opacity=0.7,
            tooltip=f"{km}km Radius"
        ).add_to(m)

# ---------------------------------------------------------
# 6. Render Map
# ---------------------------------------------------------
st_folium(m, width=1400, height=800)