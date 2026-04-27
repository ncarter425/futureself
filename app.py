import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from st_supabase_connection import SupabaseConnection # Install with: pip install st-supabase-connection

# 1. DATABASE CONNECTION
# On your phone/cloud, these will come from your 'Secrets' settings
conn = st.connection("supabase", type=SupabaseConnection)

def load_habits():
    rows = conn.query("*", table="habits", ttl=0).execute()
    return pd.DataFrame(rows.data) if rows.data else pd.DataFrame(columns=["is_stopped", "habit_name", "monthly_cost", "years_active", "habit_type"])

def save_habit(name, cost, years, h_type):
    conn.table("habits").insert({"habit_name": name, "monthly_cost": cost, "years_active": years, "habit_type": h_type, "is_stopped": False}).execute()

# 2. UI SETUP
st.set_page_config(page_title="FutureSelf", layout="wide")
st.markdown("<style>.main { background-color: #FFFFFF; }</style>", unsafe_allow_html=True)

# Math Function
def get_habit_impact(monthly, active_years, total_years, rate):
    if monthly <= 0 or active_years <= 0: return 0
    r = rate / 12
    fv_at_end = monthly * (((1 + r)**(active_years * 12) - 1) / r)
    remaining_years = total_years - active_years
    return fv_at_end * ((1 + r)**(remaining_years * 12)) if remaining_years > 0 else fv_at_end

# 3. SIDEBAR
with st.sidebar:
    st.title("👤 Your Info")
    salary = st.number_input("Annual Salary ($)", value=75000)
    age = st.number_input("How old are you?", value=30)
    retire = st.number_input("Retire Age", value=65)
    horizon = retire - age
    rate = st.slider("Growth Assumption (%)", 1, 12, 7) / 100

# 4. QUICK ADD
st.title("🛡️ FutureSelf")
with st.form("quick_add", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    name = col1.text_input("New Habit Name")
    cost = col2.number_input("Monthly Cost ($)", min_value=0)
    years = col3.number_input("Years Active", value=30)
    if st.form_submit_button("Add & Save"):
        h_type = "Need 🏠" if any(x in name.lower() for x in ["rent", "car", "gas"]) else "Want ☕"
        save_habit(name, cost, years, h_type)
        st.rerun()

# 5. LOAD & DISPLAY
df = load_habits()
if not df.empty:
    st.subheader("Step 2: Review your habits")
    edited_df = st.data_editor(df, width="stretch")
    
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
else:
    st.info("Add your first habit above to begin.")
