import pandas as pd 
import streamlit as st
import plotly.express as px


# -----------------------------------------
# PAGE SETUP
# -----------------------------------------
def setup_page():
    st.set_page_config(page_title="Energy Intelligence Dashboard", layout="wide")

    st.markdown("""
                
        <style>
            /* ---------------------------
            PAGE TITLE (theme adaptive)
            --------------------------- */
            .nav-title {
                font-size: 1.35rem;
                font-weight: 700;
                color: var(--text-color) !important;   /* auto white/black */
                background: none !important;
                -webkit-background-clip: unset !important;
                -webkit-text-fill-color: var(--text-color) !important;
                opacity: 0.85;                         /* subtle soft grey effect */
            }

            /* ---------------------------
            SECTION TITLES (theme adaptive)
            --------------------------- */
            .section-title {
                font-size: 1.1rem;
                font-weight: 600;
                margin-top: 20px;
                margin-bottom: 8px;
                color: var(--text-color) !important;  /* auto white/black */
                opacity: 0.8;                          /* softer, modern */
            }

            /* ---------------------------
            METRIC VALUE
            --------------------------- */
            [data-testid="stMetricValue"] {
                font-size: 1.5rem !important;
                font-weight: 600 !important;
            }

            /* ---------------------------
            METRIC LABEL
            --------------------------- */
            [data-testid="stMetricLabel"] {
                font-size: 1.3rem !important;
                color: var(--secondary-text-color) !important; /* auto adjusts */
            }
        </style>
        """, unsafe_allow_html=True)


# -----------------------------------------
# NAVIGATION BAR
# -----------------------------------------
def render_navbar():
    with st.container():
        col_title, col_refresh, col_back = st.columns([8.5, 0.7, 0.7])

        with col_title:
            st.markdown("<div class='nav-title'>Energy Intelligence Dashboard</div>", unsafe_allow_html=True)

        with col_refresh:
            if st.button("↻", help="Refresh", use_container_width=True):
                st.rerun()

        with col_back:
            if st.button("←", help="Back to Landing", use_container_width=True):
                st.session_state.app_mode = "landing"
                st.rerun()

    st.markdown("<hr style='margin-top:0px;'>", unsafe_allow_html=True)


# -----------------------------------------
# SIDEBAR INPUTS
# -----------------------------------------
def render_sidebar():
    st.sidebar.markdown(
    "<h2 class='sidebar-title'>Dashboard Options</h2>",
    unsafe_allow_html=True
    )

    # Small helper for consistent expander sections
    def section(title, expanded=False):
        return st.sidebar.expander(title, expanded=expanded)

    # ========= FILE UPLOAD =========
    with section("📁 Upload CSV File"):
        uploaded_file = st.file_uploader(
            "Choose File", 
            type=["csv"], 
            label_visibility="collapsed"
        )
        if uploaded_file:
            st.session_state.csv_data = pd.read_csv(uploaded_file)

    # If no data, do not show the rest
    if "csv_data" not in st.session_state:
        return None

    data = st.session_state.csv_data
    data["Timestamp"] = pd.to_datetime(data["Timestamp"])
    variables = list(data.columns)[1:]

    # ========= VARIABLE SELECTOR =========
    with section("📊 Select Variable"):
        selected_var = st.selectbox(
            "Variable", 
            variables, 
            label_visibility="collapsed"
        )

    # ========= DATE RANGE =========
    with section("🗓️ Date Range"):
        min_date = data["Timestamp"].min().date()
        max_date = data["Timestamp"].max().date()

        raw_date = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            label_visibility="collapsed"
        )

        # ---- SAFE NORMALIZATION ----
        # Case 1: User selected a tuple (valid)
        if isinstance(raw_date, tuple):
            if len(raw_date) == 2:
                base_start, base_end = raw_date
            else:
                # Should never happen, but safe fallback
                base_start = base_end = raw_date[0]

        # Case 2: User selected ONLY ONE date
        else:
            base_start = base_end = raw_date



    # ========= MONTH COMPARISON =========
    with section("📅 Compare Months"):
        month_options = data["Timestamp"].dt.to_period("M").astype(str).unique()
        compare_months = st.multiselect(
            "Select Months", 
            month_options, 
            label_visibility="collapsed"
        )

    # ========= WEEK COMPARISON =========
    with section("📆 Compare Weeks"):
        week_options = data["Timestamp"].dt.to_period("W").astype(str).unique()
        compare_weeks = st.multiselect(
            "Select Weeks", 
            week_options, 
            label_visibility="collapsed"
        )

    return data, selected_var, (base_start, base_end), compare_months, compare_weeks

# -----------------------------------------
# BUILD DF FOR COMPARISON
# -----------------------------------------
def build_comparison_df(data, selected_var, date_range, months, weeks):
    base_start, base_end = date_range
    final_df = pd.DataFrame()
    trend_plot = None

    # Month comparison
    if months:
        for m in months:
            df_m = data[data["Timestamp"].dt.to_period("M").astype(str) == m]
            df_m["Period"] = m
            df_m["AlignedX"] = df_m["Timestamp"].dt.day
            final_df = pd.concat([final_df, df_m])

        trend_plot = px.line(final_df, x="AlignedX", y=selected_var, color="Period", template="plotly_dark")
        trend_plot.update_layout(xaxis_title="Day of Month")

    # Week comparison
    elif weeks:
        for w in weeks:
            df_w = data[data["Timestamp"].dt.to_period("W").astype(str) == w]
            df_w["Period"] = w
            df_w["AlignedX"] = df_w["Timestamp"].dt.weekday
            final_df = pd.concat([final_df, df_w])

        trend_plot = px.line(final_df, x="AlignedX", y=selected_var, color="Period", template="plotly_dark")
        trend_plot.update_layout(xaxis_title="Day of Week")

    # Default date range
    else:
        mask = (data["Timestamp"] >= pd.to_datetime(base_start)) & (data["Timestamp"] <= pd.to_datetime(base_end))
        final_df = data.loc[mask].copy()
        final_df["Period"] = f"{base_start} → {base_end}"

        trend_plot = px.line(final_df, x="Timestamp", y=selected_var, color="Period", template="plotly_dark")

    return final_df, trend_plot


# -----------------------------------------
# KPI SECTION
# -----------------------------------------
def render_kpis(df, selected_var):
    avg_val = df[selected_var].mean()
    max_val = df[selected_var].max()
    min_val = df[selected_var].min()

    peak_time = df.loc[df[selected_var].idxmax(), "Timestamp"] if "Timestamp" in df else "Aligned"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Average", f"{avg_val:,.2f}")
    col2.metric("Maximum", f"{max_val:,.2f}")
    col3.metric("Baseload", f"{min_val:,.2f}")
    col4.metric("Peak Occurred At", f"{peak_time}")


# -----------------------------------------
# MAIN DASHBOARD
# -----------------------------------------
def dashboard():
    setup_page()
    render_navbar()

    sidebar_out = render_sidebar()
    if sidebar_out is None:
        st.warning("Upload a CSV to begin.")
        return

    data, selected_var, date_range, months, weeks = sidebar_out

    final_df, trend_plot = build_comparison_df(data, selected_var, date_range, months, weeks)

    render_kpis(final_df, selected_var)

    st.markdown("<div class='section-title'>Data Preview</div>", unsafe_allow_html=True)
    st.dataframe(final_df, use_container_width=True, height=250)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(trend_plot, use_container_width=True)

    with col2:
        totals = final_df.groupby("Period")[selected_var].sum().reset_index()
        fig_tot = px.bar(totals, x="Period", y=selected_var, template="plotly_dark")
        st.plotly_chart(fig_tot, use_container_width=True)

def landing_page():
    
    st.markdown(
        """
        <style>
            /* -----------------------------
            HERO TITLE (gradient stays same)
            ----------------------------- */
            .hero-title {
                font-size: 3rem;
                font-weight: 800;
                text-align: center;
                margin-top: 1.5rem;
                margin-bottom: 0.3em;
                background: linear-gradient(90deg, #ff2cdf, #2dbaff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            /* -----------------------------
            HERO SUBTITLE (auto light/dark)
            ----------------------------- */
            .hero-subtitle {
                font-size: 1.2rem;
                font-weight: 300;
                text-align: center;
                color: var(--secondary-text-color) !important;
                max-width: 750px;
                margin: 0 auto;
                margin-bottom: 2.5rem;
            }

            /* -----------------------------
            VALUE HEADER (auto theme)
            ----------------------------- */
            .value-header {
                text-align: center;
                font-size: 1.6rem;
                font-weight: 600;
                margin-top: 3rem;
                margin-bottom: 2rem;
                color: var(--text-color) !important;
            }

            /* -----------------------------
            VALUE BOX (auto theme)
            ----------------------------- */
            .value-box {
                background: var(--secondary-background-color) !important;
                padding: 1.5rem;
                border-radius: 12px;
                text-align: center;

                /* Border adapts to theme:
                - Light mode → black border
                - Dark mode → white border
                */
                border: 1px solid var(--text-color) !important;

                color: var(--text-color) !important;
            }

            /* hover should also adapt */
            .value-box:hover {
                border-color: var(--secondary-text-color) !important;
                transition: 0.2s ease;
            }

            /* center button */
            .center-btn {
                display: flex;
                justify-content: center;
                margin-top: 1rem;
            }
        </style>
        """,
        unsafe_allow_html=True
    )


    # ---------- Hero Section ----------
    st.markdown("<div class='hero-title'>Energy Intelligence, Simplified</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='hero-subtitle'>Explore clean dashboards, AI-driven insights, and automated processing to better understand and optimise your energy usage.</div>",
        unsafe_allow_html=True
    )

    # ---------- Go to Dashboard Button ----------
    btn_col = st.columns([4, 2, 4])
    with btn_col[1]:
        if st.button("🚀 Go to Dashboard", use_container_width=True):
            st.session_state.app_mode = "dashboard"
            st.rerun()

    # ---------- Value Proposition ----------
    st.markdown("<div class='value-header'>What We Offer</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class='value-box'>
                <h3>Data Pipeline</h3>
                <p>Automatically clean and standardize energy data with ease.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            """
            <div class='value-box'>
                <h3>AI Insights</h3>
                <p>Instantly understand anomalies, trends, and performance drivers.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            """
            <div class='value-box'>
                <h3>Dashboards</h3>
                <p>Minimal, decision-ready dashboards designed for clarity.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ---------- Footer ----------
    st.markdown("---")
    st.markdown(
        "<p style='text-align:center;color:#999;font-size:0.85rem;'>© 2025 Energy Intelligence Platform</p>",
        unsafe_allow_html=True
    )


# ========== ROUTER LOGIC ==================
# ==========================================

def router():
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "landing"   # default landing page

    if st.session_state.app_mode == "landing":
        landing_page()
    elif st.session_state.app_mode == "dashboard":
        dashboard()


# ==========================================
# ========== MAIN ENTRY ====================
# ==========================================

if __name__ == "__main__":
    st.set_page_config(layout="wide", page_icon="⚡", page_title="Energy Intelligence")
    router()
