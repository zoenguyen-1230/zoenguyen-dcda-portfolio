"""
Hometown Map - NYC Locations
Creates an interactive Folium map with custom Mapbox basemap,
geocoded addresses, and styled markers for different location types.

Author: Zoe Nguyen
Course: DCDA 40833 | Spring 2026
"""

import pandas as pd
import folium
from folium import IFrame
from branca.element import Template, MacroElement
import requests
import time

# =============================================================================
# CONFIGURATION
# =============================================================================

# Mapbox API Token
MAPBOX_TOKEN = "pk.eyJ1IjoidHVlbWluaDEyMzAiLCJhIjoiY21sdHFodDhqMDMwbDNlcHlkM2hveWdxbSJ9.LLQUTNhR_hXomCf2DMBtuw"

# Mapbox Custom Style URL (converted to tile URL format)
# Original style: mapbox://styles/tueminh1230/cmlws9q3g000j01s736tgbbir
MAPBOX_STYLE_ID = "tueminh1230/cmlws9q3g000j01s736tgbbir"
MAPBOX_TILE_URL = f"https://api.mapbox.com/styles/v1/{MAPBOX_STYLE_ID}/tiles/256/{{z}}/{{x}}/{{y}}@2x?access_token={MAPBOX_TOKEN}"

# Input/Output files
CSV_FILE = "nyc_hometown_locations.csv"
OUTPUT_HTML = "hometown_map.html"

# Map center (NYC default - will be adjusted based on locations)
DEFAULT_CENTER = [40.7128, -74.0060]
DEFAULT_ZOOM = 12

# =============================================================================
# MARKER STYLING BY LOCATION TYPE
# =============================================================================

# Define colors and icons for each location type
LOCATION_STYLES = {
    "Restaurants & Cafes": {
        "color": "red",
        "icon": "cutlery",
        "prefix": "fa"
    },
    "Cultural Sites": {
        "color": "purple",
        "icon": "university",
        "prefix": "fa"
    },
    "Parks & Recreation Areas": {
        "color": "green",
        "icon": "tree",
        "prefix": "fa"
    },
    "Shopping District or Local Businesses": {
        "color": "blue",
        "icon": "shopping-bag",
        "prefix": "fa"
    }
}

# Default style for unknown types
DEFAULT_STYLE = {
    "color": "gray",
    "icon": "map-marker",
    "prefix": "fa"
}

# =============================================================================
# GEOCODING FUNCTION
# =============================================================================

def geocode_address(address, mapbox_token):
    """
    Convert an address to latitude/longitude using Mapbox Geocoding API.
    
    Args:
        address (str): The address to geocode
        mapbox_token (str): Mapbox API access token
    
    Returns:
        tuple: (latitude, longitude) or (None, None) if geocoding fails
    """
    # URL encode the address
    encoded_address = requests.utils.quote(address)
    
    # Mapbox Geocoding API endpoint
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded_address}.json"
    
    params = {
        "access_token": mapbox_token,
        "limit": 1,
        "country": "US"  # Limit to US addresses
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("features") and len(data["features"]) > 0:
            # Mapbox returns [longitude, latitude]
            coords = data["features"][0]["center"]
            longitude, latitude = coords[0], coords[1]
            return latitude, longitude
        else:
            print(f"  ⚠️ No results found for: {address}")
            return None, None
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Geocoding error for {address}: {e}")
        return None, None

# =============================================================================
# POPUP HTML GENERATOR
# =============================================================================

def create_popup_html(name, description, image_url, location_type):
    """
    Create HTML content for marker popup with name, description, and image.
    
    Args:
        name (str): Location name
        description (str): Personal description of the location
        image_url (str): URL to an image of the location
        location_type (str): Type of location (for styling)
    
    Returns:
        str: HTML string for the popup
    """
    # Get the color for the location type
    style = LOCATION_STYLES.get(location_type, DEFAULT_STYLE)
    color = style["color"]
    
    # Create HTML with inline styling
    html = f"""
    <div style="width: 280px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <h3 style="margin: 0 0 8px 0; color: #333; font-size: 16px; border-bottom: 2px solid {color}; padding-bottom: 6px;">
            {name}
        </h3>
        <span style="display: inline-block; background: {color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-bottom: 10px;">
            {location_type}
        </span>
        <img src="{image_url}" alt="{name}" style="width: 100%; height: 150px; object-fit: cover; border-radius: 8px; margin: 8px 0;" onerror="this.style.display='none'"/>
        <p style="margin: 8px 0 0 0; color: #555; font-size: 13px; line-height: 1.5;">
            {description}
        </p>
    </div>
    """
    return html

# =============================================================================
# LEGEND GENERATOR
# =============================================================================

def create_legend_html():
    """
    Create HTML for the map legend showing all location types and their colors.
    
    Returns:
        MacroElement: A Folium-compatible legend element
    """
    # Map marker colors to CSS colors
    color_map = {
        "red": "#d63e2a",
        "purple": "#9b4f96",
        "green": "#72b026",
        "blue": "#38aadd",
        "gray": "#7b7b7b"
    }
    
    # Build legend items HTML
    legend_items = ""
    for loc_type, style in LOCATION_STYLES.items():
        css_color = color_map.get(style["color"], "#7b7b7b")
        legend_items += f"""
            <div style="display: flex; align-items: center; margin-bottom: 8px;">
                <div style="width: 20px; height: 20px; background: {css_color}; border-radius: 50%; margin-right: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.3);"></div>
                <span style="font-size: 13px; color: #333;">{loc_type}</span>
            </div>
        """
    
    template = """
    {% macro html(this, kwargs) %}
    <div id="legend" style="
        position: fixed;
        bottom: 30px;
        left: 30px;
        z-index: 1000;
        background: white;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        max-width: 280px;
    ">
        <h4 style="margin: 0 0 12px 0; font-size: 14px; color: #333; border-bottom: 1px solid #eee; padding-bottom: 8px;">
            📍 Location Types
        </h4>
        """ + legend_items + """
    </div>
    {% endmacro %}
    """
    
    macro = MacroElement()
    macro._template = Template(template)
    return macro

# =============================================================================
# MAIN MAP CREATION FUNCTION
# =============================================================================

def create_hometown_map():
    """
    Main function to create the interactive hometown map.
    Reads CSV, geocodes addresses, and creates Folium map with custom styling.
    """
    print("=" * 60)
    print("🗺️  Creating Hometown Map - NYC Locations")
    print("=" * 60)
    
    # Step 1: Read CSV file
    print("\n📂 Reading location data...")
    try:
        df = pd.read_csv(CSV_FILE)
        print(f"   ✅ Loaded {len(df)} locations from {CSV_FILE}")
    except FileNotFoundError:
        print(f"   ❌ Error: {CSV_FILE} not found!")
        return
    except Exception as e:
        print(f"   ❌ Error reading CSV: {e}")
        return
    
    # Step 2: Geocode addresses
    print("\n📍 Geocoding addresses using Mapbox API...")
    latitudes = []
    longitudes = []
    
    for idx, row in df.iterrows():
        address = row["Address"]
        print(f"   [{idx + 1}/{len(df)}] Geocoding: {row['Name']}")
        
        lat, lon = geocode_address(address, MAPBOX_TOKEN)
        latitudes.append(lat)
        longitudes.append(lon)
        
        # Small delay to avoid rate limiting
        time.sleep(0.2)
    
    df["Latitude"] = latitudes
    df["Longitude"] = longitudes
    
    # Filter out locations that couldn't be geocoded
    df_valid = df.dropna(subset=["Latitude", "Longitude"])
    print(f"\n   ✅ Successfully geocoded {len(df_valid)}/{len(df)} locations")
    
    if len(df_valid) == 0:
        print("   ❌ No valid locations to map!")
        return
    
    # Step 3: Calculate map center
    center_lat = df_valid["Latitude"].mean()
    center_lon = df_valid["Longitude"].mean()
    print(f"\n🎯 Map center: ({center_lat:.4f}, {center_lon:.4f})")
    
    # Step 4: Create Folium map with custom Mapbox basemap
    print("\n🗺️  Creating Folium map with custom Mapbox style...")
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=DEFAULT_ZOOM,
        tiles=None  # We'll add custom tiles
    )
    
    # Add custom Mapbox tile layer
    folium.TileLayer(
        tiles=MAPBOX_TILE_URL,
        attr='Map data © <a href="https://www.mapbox.com/">Mapbox</a>',
        name="Custom Mapbox Style",
        overlay=False,
        control=True
    ).add_to(m)
    
    # Step 5: Add markers for each location
    print("\n📌 Adding markers...")
    
    for idx, row in df_valid.iterrows():
        name = row["Name"]
        lat = row["Latitude"]
        lon = row["Longitude"]
        location_type = row["Type"]
        description = row["Description"]
        image_url = row["Image_URL"]
        
        # Get marker style based on location type
        style = LOCATION_STYLES.get(location_type, DEFAULT_STYLE)
        
        # Create popup HTML
        popup_html = create_popup_html(name, description, image_url, location_type)
        
        # Create iframe for popup (allows for larger, styled content)
        iframe = IFrame(popup_html, width=320, height=350)
        popup = folium.Popup(iframe, max_width=320)
        
        # Create marker with custom icon
        marker = folium.Marker(
            location=[lat, lon],
            popup=popup,
            tooltip=name,
            icon=folium.Icon(
                color=style["color"],
                icon=style["icon"],
                prefix=style["prefix"]
            )
        )
        marker.add_to(m)
        print(f"   ✅ Added: {name} ({location_type})")
    
    # Step 6: Add legend
    print("\n📋 Adding legend...")
    legend = create_legend_html()
    m.get_root().add_child(legend)
    print("   ✅ Legend added")
    
    # Step 7: Add layer control (if needed for future layers)
    folium.LayerControl().add_to(m)
    
    # Step 8: Save the map
    print(f"\n💾 Saving map to {OUTPUT_HTML}...")
    m.save(OUTPUT_HTML)
    print(f"   ✅ Map saved successfully!")
    
    # Summary
    print("\n" + "=" * 60)
    print("🎉 Map creation complete!")
    print("=" * 60)
    print(f"\n📊 Summary:")
    print(f"   • Total locations: {len(df)}")
    print(f"   • Successfully mapped: {len(df_valid)}")
    print(f"   • Output file: {OUTPUT_HTML}")
    print("\n📍 Location types:")
    for loc_type, count in df_valid["Type"].value_counts().items():
        style = LOCATION_STYLES.get(loc_type, DEFAULT_STYLE)
        print(f"   • {loc_type}: {count} ({style['color']} markers)")
    
    print(f"\n🌐 Open {OUTPUT_HTML} in your browser to view the map!")

# =============================================================================
# RUN THE SCRIPT
# =============================================================================

if __name__ == "__main__":
    create_hometown_map()
