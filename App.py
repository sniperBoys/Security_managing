import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import time
import random
import string
import hashlib

st.set_page_config(page_title="Security Tracker with OTP", page_icon="🛡️", layout="wide")

# File paths
DATA_FILE = "locations.json"
OTP_FILE = "otp_store.json"
DEVICES_FILE = "authorized_devices.json"

# Initialize session states
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_otp' not in st.session_state:
    st.session_state.current_otp = None
if 'tracking_device' not in st.session_state:
    st.session_state.tracking_device = None
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

# ============== OTP FUNCTIONS ==============
def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def save_otp(device_id, otp):
    """Save OTP with expiry"""
    try:
        if os.path.exists(OTP_FILE):
            with open(OTP_FILE, 'r') as f:
                otp_data = json.load(f)
        else:
            otp_data = {}
        
        otp_data[device_id] = {
            "otp": otp,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=5)).isoformat(),
            "used": False
        }
        
        with open(OTP_FILE, 'w') as f:
            json.dump(otp_data, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error saving OTP: {e}")
        return False

def verify_otp(device_id, entered_otp):
    """Verify OTP"""
    try:
        if not os.path.exists(OTP_FILE):
            return False, "No OTP generated yet"
        
        with open(OTP_FILE, 'r') as f:
            otp_data = json.load(f)
        
        if device_id not in otp_data:
            return False, "No OTP found for this device"
        
        otp_info = otp_data[device_id]
        
        # Check if OTP expired
        expiry = datetime.fromisoformat(otp_info['expires_at'])
        if datetime.now() > expiry:
            return False, "OTP expired (valid for 5 minutes)"
        
        # Check if already used
        if otp_info['used']:
            return False, "OTP already used"
        
        # Verify OTP
        if otp_info['otp'] == entered_otp:
            # Mark as used
            otp_data[device_id]['used'] = True
            with open(OTP_FILE, 'w') as f:
                json.dump(otp_data, f, indent=2)
            return True, "OTP verified successfully!"
        
        return False, "Invalid OTP"
    
    except Exception as e:
        return False, f"Error: {str(e)}"

def save_authorized_device(device_id):
    """Save authorized device"""
    try:
        if os.path.exists(DEVICES_FILE):
            with open(DEVICES_FILE, 'r') as f:
                devices = json.load(f)
        else:
            devices = {}
        
        devices[device_id] = {
            "authorized_at": datetime.now().isoformat(),
            "status": "active",
            "hash": hashlib.sha256(device_id.encode()).hexdigest()[:10]
        }
        
        with open(DEVICES_FILE, 'w') as f:
            json.dump(devices, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def check_device_authorized(device_id):
    """Check if device is authorized"""
    if not os.path.exists(DEVICES_FILE):
        return False
    
    with open(DEVICES_FILE, 'r') as f:
        devices = json.load(f)
    
    return device_id in devices and devices[device_id]['status'] == 'active'

# ============== LOCATION FUNCTIONS ==============
def save_location(device_id, lat, lon):
    """Save location only if device is authorized"""
    if not check_device_authorized(device_id):
        return False, "Device not authorized"
    
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
        else:
            data = {}
        
        if device_id not in data:
            data[device_id] = []
        
        data[device_id].append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "latitude": float(lat),
            "longitude": float(lon)
        })
        
        # Keep only last 1000 locations
        if len(data[device_id]) > 1000:
            data[device_id] = data[device_id][-1000:]
        
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        return True, "Location saved"
    except Exception as e:
        return False, str(e)

def load_locations(device_id=None):
    """Load locations for specific device or all"""
    if not os.path.exists(DATA_FILE):
        return {}
    
    with open(DATA_FILE, 'r') as f:
        data = json.load(f)
    
    if device_id:
        return {device_id: data.get(device_id, [])}
    return data

# ============== ADMIN AUTHENTICATION ==============
ADMIN_PASSWORD = "security2024"  # Change this!

def admin_login(password):
    if password == ADMIN_PASSWORD:
        st.session_state.admin_logged_in = True
        return True
    return False

# ============== STREAMLIT UI ==============
st.title("🛡️ Secure Location Tracking System")
st.markdown("### 🔐 OTP-Based Consent System")

# Sidebar for admin
with st.sidebar:
    if not st.session_state.admin_logged_in:
        st.header("🔑 Admin Login")
        admin_pass = st.text_input("Admin Password:", type="password")
        if st.button("Login"):
            if admin_login(admin_pass):
                st.success("✅ Logged in as Admin")
                st.rerun()
            else:
                st.error("❌ Invalid password")
    else:
        st.success("✅ Admin Access")
        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.rerun()
        
        st.divider()
        st.header("📱 Generate OTP")
        device_id = st.text_input("Device ID:", "boss_device_001")
        
        if st.button("🔢 Generate New OTP", type="primary"):
            otp = generate_otp()
            if save_otp(device_id, otp):
                st.session_state.current_otp = otp
                st.session_state.tracking_device = device_id
                st.success(f"✅ OTP Generated!")
                st.code(f"OTP: {otp}")
                st.info("⏰ Valid for 5 minutes")
                
                # Also authorize device
                save_authorized_device(device_id)
        
        if st.session_state.current_otp:
            st.info(f"""
            📱 **Share this with Boss:**
            - OTP: **{st.session_state.current_otp}**
            - Link: Your app URL
            - Expires: 5 minutes
            """)

# Main area tabs
tab1, tab2, tab3, tab4 = st.tabs(["📋 Boss's View", "🗺️ Admin Map", "📊 History", "ℹ️ How It Works"])

# ============== TAB 1: BOSS'S VIEW ==============
with tab1:
    st.header("📱 For Boss - Enter OTP to Share Location")
    st.markdown("---")
    
    # URL parameters check for boss
    params = st.query_params
    
    if 'device' in params and 'otp' in params:
        device = params['device']
        entered_otp = params['otp']
        
        # Verify OTP
        valid, message = verify_otp(device, entered_otp)
        
        if valid:
            st.success(f"✅ {message}")
            st.session_state.authenticated = True
            st.session_state.tracking_device = device
            
            st.markdown("### 🎯 Your Location is Being Shared")
            st.info("Keep this page open to share your location")
            
            # JavaScript to get browser location
            st.components.v1.html("""
                <script>
                function getLocation() {
                    if (navigator.geolocation) {
                        navigator.geolocation.getCurrentPosition(
                            function(position) {
                                // Send location every 10 seconds
                                setInterval(function() {
                                    navigator.geolocation.getCurrentPosition(function(pos) {
                                        var lat = pos.coords.latitude;
                                        var lon = pos.coords.longitude;
                                        var currentUrl = window.location.href.split('?')[0];
                                        var newUrl = currentUrl + '?device=' + 
                                            new URLSearchParams(window.location.search).get('device') + 
                                            '&otp=' + new URLSearchParams(window.location.search).get('otp') + 
                                            '&lat=' + lat + '&lon=' + lon;
                                        window.location.href = newUrl;
                                    });
                                }, 10000);
                            },
                            function(error) {
                                document.getElementById("status").innerHTML = 
                                    "❌ Please allow location access";
                            }
                        );
                    } else {
                        document.getElementById("status").innerHTML = 
                            "❌ Geolocation not supported";
                    }
                }
                getLocation();
                </script>
                <div id="status">📍 Getting location...</div>
            """, height=100)
            
            # If lat/lon in URL, save location
            if 'lat' in params and 'lon' in params:
                lat = params['lat']
                lon = params['lon']
                success, msg = save_location(device, lat, lon)
                if success:
                    st.success(f"📍 Location updated: {lat}, {lon}")
                else:
                    st.error(msg)
        
        else:
            st.error(f"❌ {message}")
    
    else:
        st.markdown("""
        ### 👋 Welcome Boss!
        
        **To share your location:**
        1. Ask admin for OTP
        2. Open this app URL with OTP
        
        **Format:** `?device=YOUR_DEVICE_ID&otp=YOUR_OTP`
        
        **Example:**
        ```
        https://your-app.streamlit.app/?device=boss_device_001&otp=123456
        ```
        """)
        
        # Manual OTP entry
        with st.form("otp_form"):
            device_input = st.text_input("Your Device ID:")
            otp_input = st.text_input("Enter OTP:", type="password")
            submit = st.form_submit_button("✅ Verify & Start Sharing")
            
            if submit:
                valid, message = verify_otp(device_input, otp_input)
                if valid:
                    st.success(message)
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error(message)

# ============== TAB 2: ADMIN MAP VIEW ==============
with tab2:
    if st.session_state.admin_logged_in:
        st.header("🗺️ Live Location Map")
        
        locations = load_locations()
        
        if locations:
            # Calculate center
            all_lats = []
            all_lons = []
            for device, locs in locations.items():
                if locs:
                    latest = locs[-1]
                    all_lats.append(latest['latitude'])
                    all_lons.append(latest['longitude'])
            
            if all_lats:
                center_lat = sum(all_lats) / len(all_lats)
                center_lon = sum(all_lons) / len(all_lons)
            else:
                center_lat, center_lon = 30.3753, 69.3451
            
            # Create map
            m = folium.Map(location=[center_lat, center_lon], zoom_start=15)
            
            colors = ['red', 'blue', 'green', 'purple', 'orange']
            for idx, (device, locs) in enumerate(locations.items()):
                if locs:
                    color = colors[idx % len(colors)]
                    
                    # Path
                    points = [[l['latitude'], l['longitude']] for l in locs]
                    if len(points) > 1:
                        folium.PolyLine(points, color=color, weight=3, opacity=0.7).add_to(m)
                    
                    # Latest marker
                    latest = locs[-1]
                    folium.Marker(
                        [latest['latitude'], latest['longitude']],
                        popup=f"""
                        <b>📱 {device}</b><br>
                        🕐 {latest['timestamp']}<br>
                        📍 {latest['latitude']:.6f}, {latest['longitude']:.6f}
                        """,
                        icon=folium.Icon(color=color, icon='user', prefix='fa')
                    ).add_to(m)
                    
                    # Circle for accuracy
                    folium.Circle(
                        [latest['latitude'], latest['longitude']],
                        radius=50,
                        color=color,
                        fill=True,
                        opacity=0.3
                    ).add_to(m)
            
            st_folium(m, width=1000, height=600)
            
            # Current status
            st.subheader("📊 Current Status")
            for device, locs in locations.items():
                if locs:
                    latest = locs[-1]
                    st.metric(
                        f"📱 {device}",
                        f"{latest['latitude']:.4f}, {latest['longitude']:.4f}",
                        f"Updated: {latest['timestamp']}"
                    )
            
            # Auto refresh
            time.sleep(5)
            st.rerun()
        else:
            st.info("📍 No location data yet. Generate OTP to start tracking.")
    else:
        st.warning("⚠️ Please login as Admin from sidebar first")

# ============== TAB 3: HISTORY ==============
with tab3:
    if st.session_state.admin_logged_in:
        st.header("📊 Location History")
        
        locations = load_locations()
        
        if locations:
            for device, locs in locations.items():
                if locs:
                    with st.expander(f"📱 {device} - {len(locs)} records"):
                        df = pd.DataFrame(locs)
                        st.dataframe(df, use_container_width=True)
                        
                        csv = df.to_csv(index=False)
                        st.download_button(
                            f"📥 Download {device} data",
                            csv,
                            f"{device}_history.csv",
                            "text/csv"
                        )
        else:
            st.info("No history available")
    else:
        st.warning("⚠️ Admin login required")

# ============== TAB 4: HOW IT WORKS ==============
with tab4:
    st.header("ℹ️ How This System Works")
    st.markdown("""
    ### 🔐 Security Features:
    
    1. **OTP-Based Consent**
       - Admin generates OTP
       - Boss enters OTP voluntarily
       - OTP expires in 5 minutes
       - Can only be used once
    
    2. **No App Installation**
       - Works in any browser
       - No need to touch boss's phone
       - Boss shares link himself
    
    3. **Full Transparency**
       - Boss knows when tracking is active
       - Can close browser to stop anytime
       - Location history visible
    
    ### 📱 Steps for Boss:
    1. Get OTP from Security Manager
    2. Open tracking link in browser
    3. Enter OTP
    4. Allow location access
    5. Keep browser open
    
    ### ⚖️ Legal Compliance:
    - ✅ Requires explicit consent via OTP
    - ✅ User can stop anytime
    - ✅ Full transparency
    - ✅ Audit trail maintained
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>🛡️ Secure Location Tracking System | OTP-Protected | Consent-Based</p>
    <p>All tracking requires explicit OTP verification</p>
</div>
""", unsafe_allow_html=True)
