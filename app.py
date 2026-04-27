import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client

# --- 1. DATABASE CONNECTION ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- 2. DATABASE FUNCTIONS ---
def load_habits():
    try:
        response = supabase.table("habits").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except:
        return pd.DataFrame()

def save_habit(name, cost, years, h_type):
    supabase.table("habits").insert({
        "habit_name": name, 
        "monthly_cost": cost, 
        "years_active": years, 
        "habit_type": h_type, 
        "is_stopped": False
    }).execute()

# NEW: Delete function
def delete_all_habits():
    # In Supabase, deleting with a 'neq' to a dummy value is a quick way to clear a table
    supabase.table("habits").delete().neq("habit_name", "dummystring").execute()

def get_habit_impact(monthly, active_years, total_years, rate):
    if monthly <= 0 or active_years <= 0: return 0
    r = rate / 12
    fv_at_end = monthly * (((1 + r)**(active_years * 12) - 1) / r)
    remaining_years = total_years - active_years
    return fv_at_end * ((1 + r)**(remaining_years * 12)) if remaining_years > 0 else fv_at_end

# --- 3. UI SETUP ---
st.set_page_config(page_title="FutureSelf", layout="wide")
st.markdown("<style>.main { background-color: #FFFFFF; }</style>", unsafe_allow_html=True)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("👤 Your Info")
    current_salary = st.number_input("Annual Salary ($)", value=75000, step=5000)
    current_age = st.number_input("Current Age", value=30)
    retire_age = st.number_input("Retire Age", value=65)
    goal_target = current_salary * 10 
    st.info(f"💡 Target goal: ${goal_target:,.0f}")
    total_horizon = retire_age - current_age
    annual_rate = st.slider("Growth Assumption (%)", 1, 12, 7) / 100

    st.divider()
    # NEW: The Clear Data Button
    st.subheader("⚠️ Danger Zone")
    if st.button("Delete All Habits", help="This will permanently wipe your database."):
        delete_all_habits()
        st.success("Database cleared!")
        st.rerun()

# --- 5. MAIN APP ---
st.title("🛡️ FutureSelf")
st.markdown("##### Most apps show what you spent. We show you the *freedom* you traded for it.")
st.divider()

# Step 1: Quick-Add
st.subheader("Step 1: Quick-Add a Habit")
with st.form("quick_add_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    new_habit = col1.text_input("Habit Name", placeholder="e.g., Weekly Takeout")
    new_cost = col2.number_input("Monthly Cost ($)", min_value=0, step=10, value=100)
    default_dur = 5 if any(x in (new_habit or "").lower() for x in ["car", "loan", "truck"]) else 30
    new_years = col3.number_input("Years Active", min_value=1, value=default_dur)
    
    if st.form_submit_button("Add & Save"):
        if new_habit:
            new_type = "Need 🏠" if any(x in new_habit.lower() for x in ["rent", "insurance", "car", "gas"]) else "Want ☕"
            save_habit(new_habit, new_cost, new_years, new_type)
            st.rerun()

# Step 2: Display
df = load_habits()
if not df.empty:
    st.subheader("Step 2: Review your habits")
    edited_df = st.data_editor(
        df,
        column_config={
            "is_stopped": st.column_config.CheckboxColumn("Stop this?"),
            "habit_name": "Habit",
            "monthly_cost": st.column_config.NumberColumn("Monthly Cost", format="$%d"),
            "years_active": "Years Active"
        },
        disabled=["habit_name", "monthly_cost", "years_active", "habit_type"],
        width="stretch" 
    )
    
    # Step 3: Calculation & Visuals
    total_lost = sum(get_habit_impact(r["monthly_cost"], r["years_active"], total_horizon, annual_rate) for _, r in edited_df.iterrows() if not r["is_stopped"])
    total_reclaimed = sum(get_habit_impact(r["monthly_cost"], r["years_active"], total_horizon, annual_rate) for _, r in edited_df.iterrows() if r["is_stopped"])
    years_lost = total_lost / current_salary if current_salary > 0 else 0
    years_gained = total_reclaimed / current_salary if current_salary > 0 else 0

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Future Cost", f"${total_lost:,.0f}")
    m2.metric("The 'Time Price'", f"{years_lost:.1f} Years")
    m3.metric("% of Savings Goal", f"{(total_lost/goal_target)*100:.0f}%")

    # Graph
    time_axis = np.arange(0, (total_horizon * 12) + 1)
    path = [sum(get_habit_impact(r["monthly_cost"], min(r["years_active"], m/12), m/12, annual_rate) for _, r in edited_df.iterrows() if not r["is_stopped"]) for m in time_axis]
    fig_line = px.area(x=time_axis/12, y=path, title="Lost Wealth Growth", template="plotly_white")
    fig_line.update_traces(line_color='#1A365D', fillcolor='rgba(26, 54, 93, 0.1)')
    st.plotly_chart(fig_line, use_container_width=True)

    # Tiles
    b1, b2 = st.columns(2)
    with b1:
        st.markdown(f'<div style="background-color:#F0FDF4; padding:25px; border-radius:8px; border-left: 6px solid #166534;"><h4 style="color:#166534; margin-top:0;">🌟 FREEDOM BOUGHT BACK</h4><p>You saved <b>{years_gained:.1f} Years</b> of life.</p></div>', unsafe_allow_html=True)
    with b2:
        st.markdown(f'<div style="background-color:#FEF2F2; padding:25px; border-radius:8px; border-left: 6px solid #991B1B;"><h4 style="color:#991B1B; margin-top:0;">⌛ REMAINING BURDEN</h4><p>You still owe <b>{years_lost:.1f} Extra Years</b> of labor.</p></div>', unsafe_allow_html=True)
else:
    st.info("Your list is empty. Add a habit above to start tracking.")
