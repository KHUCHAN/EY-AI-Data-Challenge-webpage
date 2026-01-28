import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import os

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="South Africa Water Quality Map")
st.title("📍 South Africa Water Quality & River Network")

# 2. Data Loading (Cached)
@st.cache_data
def load_data(file_path):
    """Load data (CSV or Excel) and drop rows with missing coordinates."""
    try:
        # 파일 경로 보정
        if not os.path.exists(file_path):
            if os.path.exists(file_path + " - Sheet1.csv"): 
                file_path = file_path + " - Sheet1.csv"
            elif not os.path.exists(file_path):
                return pd.DataFrame()

        if file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
            
        df.columns = df.columns.str.strip()
        
        if 'Latitude' in df.columns and 'Longitude' in df.columns:
            return df.dropna(subset=['Latitude', 'Longitude'])
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading {file_path}: {e}")
        return pd.DataFrame()

@st.cache_data
def load_river_data(file_path):
    """Load pre-processed GeoJSON river data using geopandas."""
    try:
        gdf = gpd.read_file(file_path)
        return gdf
    except Exception as e:
        return None

# Load datasets
df_train = load_data('TRAINING_SET.csv')
df_val = load_data('VALIDATION_SET.csv')
df_wastewater = load_data('Waste_Water.xlsx') 

# Load the pre-processed river GeoJSON file
rivers_gdf = load_river_data('sa_rivers_final.geojson')

# 3. Sidebar Filters
st.sidebar.header("Filter Settings")

# 데이터 표시 여부
st.sidebar.subheader("Layers")
show_train = st.sidebar.checkbox("Show Training Set (Blue)", value=True)
show_val = st.sidebar.checkbox("Show Validation Set (Red)", value=True)
show_wastewater = st.sidebar.checkbox("Show Waste Water/Dams (Green)", value=True)
show_rivers = st.sidebar.checkbox("Show River Network", value=True)

# 반경 확인 기능
st.sidebar.subheader("Analysis Tools")
radius_km = st.sidebar.selectbox(
    "Show Radius Circle (km)",
    options=[0, 1, 3, 5, 10, 20],
    format_func=lambda x: "None" if x == 0 else f"{x} km",
    index=0
)

# 4. Map Setup
data_frames = [df for df in [df_train, df_val, df_wastewater] if not df.empty]

if data_frames:
    all_coords = pd.concat([df[['Latitude', 'Longitude']] for df in data_frames])
    center_lat = all_coords['Latitude'].mean()
    center_lon = all_coords['Longitude'].mean()
else:
    center_lat, center_lon = -30.0, 25.0

# Google Satellite 테마
m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=6,
    tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    attr='Google'
)

# 5. Add Rivers (GeoJSON Based)
if show_rivers and rivers_gdf is not None:
    unique_main_rivers = rivers_gdf['MAIN_RIV'].unique()
    colormap = plt.get_cmap('tab20') 
    river_color_map = {}
    for i, riv_id in enumerate(unique_main_rivers):
        rgba = colormap(i % 20)
        river_color_map[riv_id] = mcolors.to_hex(rgba)

    folium.GeoJson(
        rivers_gdf,
        name="River Network",
        style_function=lambda x: {
            'color': river_color_map.get(x['properties']['MAIN_RIV'], '#00FFFF'), 
            'weight': x['properties'].get('ORD_STRA', 1) * 0.5 + 0.5,
            'opacity': 0.8
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['MAIN_RIV', 'ORD_STRA'], 
            aliases=['Main River ID:', 'River Order:']
        )
    ).add_to(m)

# 6. Add Markers & Radius Circles
def add_markers_and_radius(df, color, fill_color, group_label, desc_col=None, marker_size=5, with_radius=True):
    if df.empty: return
    
    agg_dict = {'Latitude': 'size'} 
    if desc_col and desc_col in df.columns:
        agg_dict[desc_col] = 'first'
        
    distinct_df = df.groupby(['Latitude', 'Longitude']).agg(
        Count=('Latitude', 'size'),
        Name=(desc_col, 'first') if desc_col and desc_col in df.columns else ('Latitude', lambda x: None)
    ).reset_index()

    for _, row in distinct_df.iterrows():
        lat, lon = row['Latitude'], row['Longitude']
        site_name = row['Name'] if row['Name'] else group_label
        
        # 1. 마커 추가
        popup_html = f"""
        <div style="font-family: sans-serif; width: 200px;">
            <h4 style="margin-bottom: 5px;">{site_name}</h4>
            <b>Type:</b> {group_label}<br>
            <b>Samples:</b> {row['Count']}
        </div>
        """
        
        folium.CircleMarker(
            location=[lat, lon],
            radius=marker_size,
            color=color, 
            fill=True, 
            fill_color=fill_color, 
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=site_name
        ).add_to(m)
        
        # 2. 반경 원 그리기
        # [UPDATED] 원 색상을 검정('black')으로 변경하고, 두께(weight)를 2로 설정
        if with_radius and radius_km > 0:
            folium.Circle(
                location=[lat, lon],
                radius=radius_km * 1000,
                color='black',      # 잘 보이도록 검정색 사용
                weight=2,           # 두께 2배
                fill=False,
                dash_array='5, 5',
                opacity=1.0,        # 불투명도 최대
                tooltip=f"{radius_km}km Radius from {site_name}"
            ).add_to(m)

# Apply markers with updated logic
if show_train: 
    add_markers_and_radius(df_train, 'dodgerblue', 'cyan', 'Training Set', marker_size=5, with_radius=True)
if show_val: 
    add_markers_and_radius(df_val, 'darkred', 'red', 'Validation Set', marker_size=5, with_radius=True)

# [UPDATED] Waste Water 마커 크기 1.25로 축소 (2.5 -> 1.25)
if show_wastewater:
    add_markers_and_radius(df_wastewater, 'lime', '#39FF14', 'Waste Water / Dam', desc_col='Description', marker_size=1.25, with_radius=False)

# 7. Render Map
st_folium(m, width=1200, height=750, returned_objects=[])

# Footer
river_count = len(rivers_gdf) if rivers_gdf is not None else 0
ww_count = len(df_wastewater) if not df_wastewater.empty else 0
st.info(f"Loaded {river_count} river reaches. | Loaded {ww_count} waste water/dam sites.")