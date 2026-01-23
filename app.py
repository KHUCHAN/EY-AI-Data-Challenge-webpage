import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="South Africa Water Quality Map")
st.title("📍 South Africa Water Quality & River Network")

# 2. Data Loading (Cached)
@st.cache_data
def load_data(file_path):
    """Load CSV data and drop rows with missing coordinates."""
    try:
        df = pd.read_csv(file_path)
        return df.dropna(subset=['Latitude', 'Longitude'])
    except FileNotFoundError:
        return pd.DataFrame()

@st.cache_data
def load_river_data(file_path):
    """Load pre-processed GeoJSON river data using geopandas."""
    try:
        gdf = gpd.read_file(file_path)
        return gdf
    except Exception as e:
        st.error(f"Error loading river file: {e}")
        return None

# Load datasets
df_train = load_data('TRAINING_SET.csv')
df_val = load_data('VALIDATION_SET.csv')
# Load the pre-processed river GeoJSON file
rivers_gdf = load_river_data('sa_rivers_final.geojson')

# 3. Sidebar Filters
st.sidebar.header("Filter Settings")
show_train = st.sidebar.checkbox("Show Training Set (Blue)", value=True)
show_val = st.sidebar.checkbox("Show Validation Set (Red)", value=True)
show_rivers = st.sidebar.checkbox("Show River Network", value=True)

# 4. Map Setup
# Calculate center of the map based on available data points
all_coords = pd.concat([df_train[['Latitude', 'Longitude']], df_val[['Latitude', 'Longitude']]])
center_lat = all_coords['Latitude'].mean() if not all_coords.empty else -30.0
center_lon = all_coords['Longitude'].mean() if not all_coords.empty else 25.0

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=6,
    tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    attr='Google'
)

# 5. Add Rivers (GeoJSON Based)
# 5. Add Rivers (GeoJSON Based)
if show_rivers and rivers_gdf is not None:
    # 5-1. 고유한 MAIN_RIV 목록 추출 및 색상 맵 생성
    unique_main_rivers = rivers_gdf['MAIN_RIV'].unique()
    
    # 여러 하천을 구분하기 위해 Matplotlib의 colormap(예: tab20) 사용
    colormap = plt.get_cmap('tab20') 
    
    # 각 MAIN_RIV ID에 고유한 Hex 색상 매핑
    river_color_map = {}
    for i, riv_id in enumerate(unique_main_rivers):
        rgba = colormap(i % 20) # 20가지 색상을 순환하며 할당
        river_color_map[riv_id] = mcolors.to_hex(rgba)

    # 5-2. 지도에 적용
    folium.GeoJson(
        rivers_gdf,
        name="River Network",
        style_function=lambda x: {
            'color': river_color_map.get(x['properties']['MAIN_RIV'], '#87CEFA'), # 매핑된 색상 적용
            'weight': x['properties'].get('ORD_STRA', 1) * 0.25,
            'opacity': 0.8 # 색상 구분을 위해 불투명도를 살짝 올림
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['MAIN_RIV', 'ORD_STRA'], 
            aliases=['Main River ID:', 'River Order:']
        )
    ).add_to(m)

# 6. Add Markers for Sampling Stations
def add_markers(df, color, fill_color, label):
    """Add circle markers for distinct locations to the map."""
    if df.empty: return
    # Count occurrences per location to display in popup
    distinct_df = df.groupby(['Latitude', 'Longitude']).size().reset_index(name='Count')
    for _, row in distinct_df.iterrows():
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=4, 
            color=color, 
            fill=True, 
            fill_color=fill_color, 
            fill_opacity=0.7,
            popup=f"<b>[{label}]</b><br>Samples: {row['Count']}"
        ).add_to(m)

# Apply station markers to the map
if show_train: add_markers(df_train, 'dodgerblue', 'cyan', 'Training')
if show_val: add_markers(df_val, 'darkred', 'red', 'Validation')

# 7. Render Map
st_folium(m, width=1200, height=750, returned_objects=[])

# Display Footer Information
st.info(f"Loaded {len(rivers_gdf) if rivers_gdf is not None else 0} river reaches from local file.")