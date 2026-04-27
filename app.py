import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client

# --- 1. DATABASE CONNECTION ---
# This looks for SUPABASE_URL and SUPABASE_KEY in your Streamlit Secrets
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- 2. FUNCTIONS (Defined before they are called) ---
def load_habits():
    try:
        response = supabase.table("habits").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Database Error: {e}")
        return pd.DataFrame()

def save_habit(name, cost, years, h_type):
    try:
        supabase.table("habits").insert({
            "habit_name": name, 
            "monthly_cost": cost, 
            "years_active": years, 
            "habit_type": h_type, 
            "is_stopped": False
        }).execute()
    except Exception as e:
        st.error(f"Failed to save: {e}")

def get_habit_impact(monthly, active_years, total_years, rate):
    if monthly <= 0 or active_years <= 0: return 0
    r = rate / 12
    fv_at_end = monthly * (((1 + r)**(active_years * 12) - 1) / r)
    remaining_years = total_years - active_years
    return fv_at_end * ((1 + r)**(remaining_years * 12)) if remaining_years > 0 else fv_at_end

# --- 3. UI SETUP ---
st.set_page_config(page_title="FutureSelf", layout="wide")
st.markdown("<style>.main { background-color: #FFFFFF; }</style>", unsafe_allow_html=True)

# 4. SIDEBAR
with st.sidebar:
    st.title("👤 Your Info")
    salary = st.number_input("Annual Salary ($)", value=75000)
    age = st.number_input("How old are you?", value=30)
    retire = st.number_input("Retire Age", value=65)
    horizon = retire - age
    rate = st.slider("Growth Assumption (%)", 1, 12, 7) / 100

# 5. QUICK ADD FORM
st.title("🛡️ FutureSelf")
st.markdown("##### Visualizing your path to financial freedom.")

with st.form("quick_add", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    name = col1.text_input("New Habit Name")
    cost = col2.number_input("Monthly Cost ($)", min_value=0)
    years = col3.number_input("Years Active", value=30)
    if st.form_submit_button("Add & Save"):
        if name:
            h_type = "Need 🏠" if any(x in name.lower() for x in ["rent", "car", "gas"]) else "Want ☕"
            save_habit(name, cost, years, h_type)
            st.rerun()
        else:
            st.warning("Please enter a habit name.")

# 6. LOAD & DISPLAY
df = load_habits()

if not df.empty:
    st.subheader("Step 2: Review your habits")
    
    # We use the data editor to let you toggle 'is_stopped'
    edited_df = st.data_editor(
        df, 
        column_config={
            "is_stopped": st.column_config.CheckboxColumn("Stop this?"),
            "habit_name": "Habit",
            "monthly_cost": st.column_config.NumberColumn("Monthly Cost", format="$%d"),
            "years_active": "Years Active",
            "habit_type": "Type"
        },
        disabled=["habit_name", "monthly_cost", "years_active", "habit_type"], # Only allow checking the box
        width="stretch"
    )
    
    # CALCULATIONS
    total_lost = sum(get_habit_impact(r["monthly_cost"], r["years_active"], horizon, rate) for _, r in edited_df.iterrows() if not r["is_stopped"])
    years_lost = total_lost / salary if salary > 0 else 0

    # VISUALS
    st.divider()
    m1, m2 = st.columns(2)
    m1.metric("Total Future Cost", f"${total_lost:,.0f}")
    m2.metric("Extra Years of Work", f"{years_lost:.1f}")

    # Reality Tiles
    b1, b2 = st.columns(2)
    with b1:
        st.markdown(f'<div style="background-color:#F0FDF4; padding:20px; border-radius:8px; border-left: 6px solid #166534;"><h4 style="color:#166534; margin-top:0;">🌟 FREEDOM IMPACT</h4><p>Current choices require <b>{years_lost:.1f} extra years</b> of labor.</p></div>', unsafe_allow_html=True)
    with b2:
        st.markdown(f'<div style="background-color:#FEF2F2; padding:20px; border-radius:8px; border-left: 6px solid #991B1B;"><h4 style="color:#991B1B; margin-top:0;">⌛ THE WORK BURDEN</h4><p>You are trading <b>{years_lost:.1f} years</b> of your life for these habits.</p></div>', unsafe_allow_html=True)
else:
    st.info("Add your first habit above to begin.")
