import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import glob
import streamlit.components.v1 as components

# --- 1. PASSWORD PROTECTION ---
def check_password():
    """Returns True if the user had the correct password."""
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    # If already correct, return True
    if st.session_state["password_correct"]:
        return True

    # Show input for password
    placeholder = st.empty()
    with placeholder.container():
        st.write("## 🔒 Dashboard Login")
        password = st.text_input("Password", type="password")
        if password:
            if password == st.secrets["APP_PASSWORD"]:
                st.session_state["password_correct"] = True
                placeholder.empty() # Clear the login form
                st.rerun()
            else:
                st.error("😕 Password incorrect")
    return False

if check_password():   
    # --- Header Images ---
    # Using columns to place images at the extreme left and right
    col_img1, col_mid, col_img2 = st.columns([1, 8, 1])

    with col_img1:
        # Replace 'image1.png' with your actual file path or URL
        #st.image("image1.png", width=100) 
        img_1 = st.secrets["IMG1"]
        st.markdown(
            f'<img src="data:image/png;base64,{img_1}" width="100">',
            unsafe_allow_html=True
        )

    with col_img2:
        # Replace 'image2.png' with your actual file path or URL
        #st.image("image2.png", width=100)
        img_2 = st.secrets["IMG2"]
        st.markdown(
            f'<img src="data:image/png;base64,{img_2}" width="100">',
            unsafe_allow_html=True
        )
# ---------------------------------

    # --- PAGE CONFIGURATION ---
    st.set_page_config(page_title="Indonesia Tourism Dashboard", layout="wide")
    st.title("🇮🇩 Indonesia Tourism Statistics Dashboard")

    # --- 1. DATA LOADING WITH ENCODING FIX ---
    @st.cache_data
    def load_data():
        files = glob.glob("*Data*.csv")
        if not files:
            st.error("No CSV data files found in the current directory.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        df_general = pd.DataFrame()
        df_nationality = pd.DataFrame()
        df_residence = pd.DataFrame()
        df_guests = pd.DataFrame()

        for f in files:
            try:
                df = pd.read_csv(f, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(f, encoding='latin1')
                
            if '03600100' in f:
                df_general = df
            elif '03600121' in f:
                df_nationality = df
            elif '03600122' in f:
                df_residence = df
            elif '03600712' in f:
                df_guests = df

        return df_general, df_nationality, df_residence, df_guests

    df_general, df_nationality, df_residence, df_guests = load_data()

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Filters")
    available_years = []
    for d in [df_general, df_nationality, df_residence, df_guests]:
        if not d.empty:
            available_years.extend(d['year'].dropna().unique())

    if available_years:
        min_year, max_year = int(min(available_years)), int(max(available_years))
        selected_year_range = st.sidebar.slider("Select Year Range", min_year, max_year, (min_year, max_year))
    else:
        st.error("No year data available to filter.")
        st.stop()


    # --- DASHBOARD LAYOUT (TOP SECTION: MAP & TABLE) ---
    st.header("Inbound Tourism Map")

    # Dropdown to select which country-level dataset to view on the map
    map_option = st.selectbox(
        "Select Geographic Metric to Display:",
        ("Inbound Trips by Nationality", "Inbound Trips by Area of Residence", "Hotel Guests by Area of Residence")
    )

    # Map selection logic
    df_map_source = pd.DataFrame()
    value_label = "Trips (Thousands)"

    if map_option == "Inbound Trips by Nationality":
        df_map_source = df_nationality
    elif map_option == "Inbound Trips by Area of Residence":
        df_map_source = df_residence
    elif map_option == "Hotel Guests by Area of Residence":
        df_map_source = df_guests
        value_label = "Guests (Thousands)"

    if not df_map_source.empty:
        # Filter by Year
        df_filtered = df_map_source[
            (df_map_source['year'] >= selected_year_range[0]) & 
            (df_map_source['year'] <= selected_year_range[1])
        ]
        
        # Exclude aggregate regions to get pure country data for the map
        exclude_areas = ['World', 'Africa (UNWTO total)', 'Europe', 'Asia', 'Americas', 'Middle East', 'Not specified', 'East Asia and the Pacific', 'South Asia']
        df_countries = df_filtered[~df_filtered['partner_area_label'].isin(exclude_areas)]
        
        # Aggregate map data
        df_map_data = df_countries.groupby('partner_area_label')['value'].sum().reset_index()
        
        if not df_map_data.empty:
            # Create a 2/3 and 1/3 split layout
            col_map, col_table = st.columns([2, 1])

            with col_map:
                # Add Logarithmic values for smooth map coloring
                df_map_data['Log Value'] = np.log10(df_map_data['value'].clip(lower=1))
                
                # Create Choropleth Map 
                fig_map = px.choropleth(
                    df_map_data,
                    locations="partner_area_label",
                    locationmode="country names",  
                    color="Log Value", # Use log for color scaling
                    hover_name="partner_area_label",
                    hover_data={"Log Value": False, "value": True}, # Hide Log value on hover, show raw value
                    color_continuous_scale="RdYlGn", 
                    title=f"Global Origins: {map_option} ({selected_year_range[0]}-{selected_year_range[1]})",
                )
                
                # Format hover to show actual numeric values
                fig_map.update_traces(
                    hovertemplate="<b>%{hovertext}</b><br>" + value_label + ": %{customdata[0]:,.1f}<extra></extra>"
                )
                
                # Custom colorbar to display actual numbers mapping to log intervals
                max_log = int(np.ceil(df_map_data['Log Value'].max())) if not df_map_data.empty else 1
                tickvals = list(range(max_log + 1))
                ticktext = [f"{10**i:,.0f}" for i in tickvals]
                
                fig_map.update_layout(
                    geo=dict(showframe=False, showcoastlines=True, projection_type='equirectangular'),
                    margin={"r":0,"t":40,"l":0,"b":0},
                    coloraxis_colorbar=dict(title=value_label, tickvals=tickvals, ticktext=ticktext)
                )
                st.plotly_chart(fig_map, use_container_width=True)
            
            with col_table:
                # --- HIGHLIGHT STATISTICS ---
                st.markdown(f"**Key Highlights ({selected_year_range[0]}-{selected_year_range[1]})**")
                
                # Compute total sum for map data
                total_val = df_map_data['value'].sum()
                
                # Compute averages/sums from the general aggregate dataset
                df_gen_range = df_general[(df_general['year'] >= selected_year_range[0]) & (df_general['year'] <= selected_year_range[1])]
                
                los_series = df_gen_range[df_gen_range['indicator_label'] == 'inbound - trips - length of stay - average - total - visitors']['value']
                avg_stay = los_series.mean() if not los_series.empty else np.nan
                
                exp_series = df_gen_range[df_gen_range['indicator_label'] == 'inbound - expenditure - balance of payments - travel - visitors']['value']
                total_exp = exp_series.sum() if not exp_series.empty else np.nan
                
                # Metrics Layout (2 side-by-side, 1 full width)
                m1, m2 = st.columns(2)
                metric_name = "Trips" if "Trips" in value_label else "Guests"
                m1.metric(f"Total {metric_name}", f"{total_val:,.0f}k")
                
                if pd.notna(avg_stay):
                    m2.metric("Avg Stay", f"{avg_stay:,.1f} Days")
                else:
                    m2.metric("Avg Stay", "N/A")
                    
                if pd.notna(total_exp) and total_exp > 0:
                    st.metric("Total Expenditure", f"${total_exp:,.0f} Million USD")
                else:
                    st.metric("Total Expenditure", "N/A")
                
                # --- RAW DATA TABLE ---
                st.markdown(f"**Raw Data: {map_option}**")
                table_display = df_filtered[['year', 'partner_area_label', 'value']].copy()
                table_display.columns = ['Year', 'Country/Region', value_label]
                
                # Reduced height to ~230 to fit the metrics above it and perfectly match the map height
                st.dataframe(table_display, use_container_width=True, height=220)
        else:
            st.info("No map data available for the selected range.")
    else:
        st.info("Dataset not found.")


    st.markdown("---")


    # --- DASHBOARD LAYOUT (BOTTOM SECTION: AGGREGATE CHARTS) ---
    if not df_general.empty:
        df_gen_filtered = df_general[(df_general['year'] >= selected_year_range[0]) & (df_general['year'] <= selected_year_range[1])]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Transport Mode")
            transport_indicators = [
                'inbound - trips - transport - air - overnight visitors (tourists)',
                'inbound - trips - transport - water - overnight visitors (tourists)',
                'inbound - trips - transport - road - overnight visitors (tourists)',
                'inbound - trips - transport - by land - overnight visitors (tourists)'
            ]
            df_transport = df_gen_filtered[df_gen_filtered['indicator_label'].isin(transport_indicators)]
            
            if not df_transport.empty:
                df_transport = df_transport.copy()
                df_transport['Transport Mode'] = df_transport['indicator_label'].apply(
                    lambda x: x.split(' - ')[3].capitalize()
                )
                transport_agg = df_transport.groupby('Transport Mode')['value'].sum().reset_index()
                
                fig_trans = px.pie(transport_agg, values='value', names='Transport Mode', color_discrete_sequence=px.colors.qualitative.Set2)
                fig_trans.update_traces(hovertemplate="<b>%{label}</b><br>Trips: %{value:,.1f} (Thousands)<br>Percentage: %{percent}<extra></extra>")
                fig_trans.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=300)
                st.plotly_chart(fig_trans, use_container_width=True)
            else:
                st.info("No Transport data available.")

        with col2:
            st.subheader("Average Length of Stay")
            los_indicator = 'inbound - trips - length of stay - average - total - visitors'
            df_los = df_gen_filtered[df_gen_filtered['indicator_label'] == los_indicator]
            
            if not df_los.empty:
                fig_los = px.line(df_los.sort_values('year'), x='year', y='value', markers=True, labels={'value': 'Days', 'year': 'Year'}, line_shape="spline")
                fig_los.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=300)
                st.plotly_chart(fig_los, use_container_width=True)
            else:
                st.info("No Length of Stay data available.")

        with col3:
            st.subheader("Tourist Expenditure")
            exp_indicator = 'inbound - expenditure - balance of payments - travel - visitors'
            df_exp = df_gen_filtered[df_gen_filtered['indicator_label'] == exp_indicator]
            
            if not df_exp.empty:
                fig_exp = px.bar(df_exp.sort_values('year'), x='year', y='value', labels={'value': 'Expenditure (Million USD)', 'year': 'Year'}, color_discrete_sequence=['#2ca02c'])
                fig_exp.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=300)
                st.plotly_chart(fig_exp, use_container_width=True)
            else:
                st.info("No Expenditure data available.")