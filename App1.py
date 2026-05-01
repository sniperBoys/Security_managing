import streamlit as st
import json
import os
from datetime import datetime, timedelta
import random
import time

# Try importing folium - if fails, show map differently
try:
    import folium
    from streamlit_folium import st_folium
    MAP_AVAILABLE = True
except:
    MAP_AVAILABLE = False

st.set_page_config(page_title="Security Tracker", page_icon="🛡️", layout="wide")

# Files
DATA_FILE = "locations.json"
OTP_FILE = "otp_store.json"

# Session states
if 'current_otp' not in st.session_state:
    st.session_state.current_otp = None
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

# ============ FUNCTIONS ============
def generate_otp():
    return ''.join(random.choices('0123456789', k=6))

def save_otp(device_id, otp):
    try:
        otp_data = {}
        if os.path.exists(OTP_FILE):
            with open(OTP_FILE, 'r') as f:
                otp_data = json.load(f)
        
        otp_data[device_id] = {
            "otp": otp,
            "created": datetime.now().isoformat(),
            "expires": (datetime.now() + timedelta(minutes=5)).isoformat(),
            "used": False
        }
        
        with open(OTP_FILE, 'w') as f:
            json.dump(otp_data, f)
        return True
    except:
        return False

def verify_otp(device_id, entered_otp):
    try:
        if not os.path.exists(OTP_FILE):
            return False, "No OTP generated"
        
        with open(OTP_FILE, 'r') as f:
            otp_data = json.load(f)
        
        if device_id not in otp_data:
            return False, "Invalid device"
        
        otp_info = otp_data[device_id]
        expiry = datetime.fromisoformat(otp_info['expires'])
        
        if datetime.now() > expiry:
            return False, "OTP expired"
        if otp_info['used']:
            return False, "OTP already used"
        if otp_info['otp'] == entered_otp:
            otp_data[device_id]['used'] = True
            with open(OTP_FILE, 'w') as f:
                json.dump(otp_data, f)
            return True, "Verified!"
        
        return False, "Invalid OTP"
    except:
        return False, "Error"

def save_location(device_id, lat, lon):
    try:
        data = {}
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
        
        if device_id not in data:
            data[device_id] = []
        
        data[device_id].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "lat": float(lat),
            "lon": float(lon)
        })
        
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)
        return True
    except:
        return False

def load_locations():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

# ============ UI ============
st.title("🛡️ Security Location Tracker")
st.markdown("### 🔐 OTP-Based Consent System")

# Get URL parameters
params = st.query_params

# ============ BOSS VIEW (TAB 1) ============
boss_tab, admin_tab = st.tabs(["📱 Boss View", "🔐 Admin Panel"])

with boss_tab:
    st.header("📍 Share Your Location")
    
    # Check if OTP verification from URL
    if 'device' in params and 'otp' in params:
        device = params['device']
        otp = params['otp']
        
        valid, msg = verify_otp(device, otp)
        
        if valid:
            st.success(f"✅ {msg}")
            st.info("📍 Share your location to start tracking")
            
            # Get browser location via JavaScript
            st.components.v1.html("""
                <script>
                function sendLocation() {
                    if (navigator.geolocation) {
                        navigator.geolocation.getCurrentPosition(function(pos) {
                            var lat = pos.coords.latitude;
                            var lon = pos.coords.longitude;
                            var url = window.location.href.split('?')[0];
                            var device = new URLSearchParams(window.location.search).get('device');
                            var otp = new URLSearchParams(window.location.search).get('otp');
                            window.location.href = url + '?device=' + device + '&otp=' + otp + '&lat=' + lat + '&lon=' + lon;
                        });
                    }
                }
                sendLocation();
                setInterval(sendLocation, 30000);
                </script>
                <p style='color:green;font-size:20px;'>📍 Sending location...</p>
            """, height=80)
            
            if 'lat' in params and 'lon' in params:
                if save_location(device, params['lat'], params['lon']):
                    st.success(f"✅ Location updated: {params['lat']}, {params['lon']}")
                    st.metric("Latitude", params['lat'])
                    st.metric("Longitude", params['lon'])
        else:
            st.error(f"❌ {msg}")
    
    # Manual OTP Entry
    with st.form("otp_entry"):
        st.subheader("Enter OTP to Share Location")
        device_id = st.text_input("Device ID:", "boss_device")
        otp_input = st.text_input("Enter 6-digit OTP:", max_chars=6)
        
        if st.form_submit_button("✅ Verify & Share Location"):
            valid, msg = verify_otp(device_id, otp_input)
            if valid:
                st.success(msg)
                st.info("Please allow location access when prompted")
                # Reload with OTP in URL
                st.markdown(f"""
                <script>
                window.location.href = window.location.href.split('?')[0] + 
                    '?device={device_id}&otp={otp_input}';
                </script>
                """, unsafe_allow_html=True)
            else:
                st.error(msg)

# ============ ADMIN PANEL (TAB 2) ============
with admin_tab:
    st.header("🔐 Admin Panel")
    
    # Admin Login
    if not st.session_state.admin_logged_in:
        admin_pass = st.text_input("Admin Password:", type="password")
        if st.button("🔑 Login"):
            if admin_pass == "admin123":  # Change this password
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("Wrong password")
    else:
        st.success("✅ Logged in")
        
        # Generate OTP
        st.subheader("📱 Generate OTP")
        device_name = st.text_input("Device Name:", "boss_phone")
        
        if st.button("🔢 Generate OTP", type="primary"):
            otp = generate_otp()
            if save_otp(device_name, otp):
                st.session_state.current_otp = otp
                st.success("✅ OTP Generated!")
                st.markdown(f"""
                ### OTP: **{otp}**
                ⏰ Valid for 5 minutes
                
                📱 **Send this to Boss:**
                ```
                Link: [Your App URL]/?device={device_name}&otp={otp}
                ```
                """)
        
        st.divider()
        
        # View Locations
        st.subheader("📍 Live Locations")
        
        locations = load_locations()
        
        if locations:
            for device, locs in locations.items():
                if locs:
                    latest = locs[-1]
                    with st.expander(f"📱 {device} - Last: {latest['date']} {latest['time']}"):
                        st.write(f"**Latitude:** {latest['lat']}")
                        st.write(f"**Longitude:** {latest['lon']}")
                        st.write(f"**Total Records:** {len(locs)}")
                        
                        # Show all records
                        st.dataframe(locs)
            
            # Map
            if MAP_AVAILABLE:
                st.subheader("🗺️ Map View")
                try:
                    all_lats = []
                    all_lons = []
                    for locs in locations.values():
                        if locs:
                            latest = locs[-1]
                            all_lats.append(latest['lat'])
                            all_lons.append(latest['lon'])
                    
                    if all_lats:
                        center_lat = sum(all_lats) / len(all_lats)
                        center_lon = sum(all_lons) / len(all_lons)
                        
                        m = folium.Map(location=[center_lat, center_lon], zoom_start=15)
                        
                        for device, locs in locations.items():
                            if locs:
                                latest = locs[-1]
                                folium.Marker(
                                    [latest['lat'], latest['lon']],
                                    popup=f"{device}<br>{latest['time']}"
                                ).add_to(m)
                        
                        st_folium(m, width=700, height=400)
                except:
                    st.warning("Map temporarily unavailable")
            else:
                st.info("Map module loading...")
        else:
            st.info("No location data yet")
        
        # Auto refresh
        time.sleep(10)
        st.rerun()

# Footer
st.markdown("---")
st.markdown("<p style='text-align:center;'>🛡️ Secure Tracking | OTP Protected | Consent Based</p>", unsafe_allow_html=True)
