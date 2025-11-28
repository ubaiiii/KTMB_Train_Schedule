import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIG ---
st.set_page_config(
    page_title="KTM Train Schedule",
    page_icon="🚆",
    layout="centered"
)

# --- GLOBAL TIME ---
# kl_time = datetime.now()
kl_time = datetime.now() + timedelta(hours=8)  # UTC+8 for Kuala Lumpur
time_depart = kl_time.time().replace(second=0, microsecond=0)

# --- CACHE FILE LOADING ---
@st.cache_data
def load_parquet(path):
    return pd.read_parquet(path)


# --- TIME HELPERS ---
def parse_time_to_minutes(t):
    """Convert timetable value into minutes since midnight."""
    t_str = str(t).strip()
    if ":" in t_str:
        h, m = t_str.split(":")
    elif len(t_str) <= 3:  # e.g. "615" -> "6:15"
        h, m = "0", t_str.zfill(2)
    else:  # e.g. "1026" -> "10:26"
        h, m = t_str[:-2], t_str[-2:]
    return int(h) * 60 + int(m)


def get_train_schedules(file_map, selected_route, selected_schedule, departure, destination, filter_time=None):
    key = (selected_route, selected_schedule)
    if key not in file_map:
        return pd.DataFrame()

    files = file_map[key]
    if len(files) != 2:
        return pd.DataFrame()

    try:
        df1, df2 = load_parquet(files[0]), load_parquet(files[1])
    except Exception:
        return pd.DataFrame()

    # Pick the dataframe where departure appears first
    idx1 = df1.index[df1['STATION'] == departure].tolist()
    idx2 = df2.index[df2['STATION'] == departure].tolist()
    chosen_df = df1 if (idx1 and (not idx2 or idx1[0] <= idx2[0])) else df2

    if departure not in chosen_df['STATION'].values or destination not in chosen_df['STATION'].values:
        return pd.DataFrame()

    valid_services = []
    for col in chosen_df.columns[1:]:
        dep_time = chosen_df.loc[chosen_df['STATION'] == departure, col].values[0]
        dest_time = chosen_df.loc[chosen_df['STATION'] == destination, col].values[0]

        if pd.isna(dep_time) or pd.isna(dest_time):
            continue

        dep_time_str, dest_time_str = str(dep_time).strip(), str(dest_time).strip()
        if not dep_time_str or not dest_time_str:
            continue

        # Filter based on current/custom time if provided
        if filter_time is not None:
            try:
                dep_minutes = parse_time_to_minutes(dep_time_str)
                if dep_minutes < filter_time:
                    continue
            except Exception:
                pass

        valid_services.append({
            "Service_ID": col,
            "Departure_Station": departure,
            "Departure_Time": dep_time_str,
            "Arrival_Station": destination,
            "Arrival_Time": dest_time_str
        })

    return pd.DataFrame(valid_services)


# --- FILE MAPPING ---
file_map = {
    ("Batu Caves - Pulau Sebang", "Weekdays"): [
        "timetables/batu_caves_weekdays_route_1.parquet",
        "timetables/batu_caves_weekdays_route_2.parquet",
    ],
    ("Batu Caves - Pulau Sebang", "Weekends"): [
        "timetables/batu_caves_weekends_route_1.parquet",
        "timetables/batu_caves_weekends_route_2.parquet",
    ],
    ("Tanjung Malim - Pelabuhan Klang", "Weekdays"): [
        "timetables/klang_weekdays_route_1.parquet",
        "timetables/klang_weekdays_route_2.parquet",
    ],
    ("Tanjung Malim - Pelabuhan Klang", "Weekends"): [
        "timetables/klang_weekends_route_1.parquet",
        "timetables/klang_weekends_route_2.parquet",
    ],
    ("Padang Besar - Butterworth", "Not applicable"): [
        "timetables/utara_padangbesar_1.parquet",
        "timetables/utara_padangbesar_2.parquet",
    ],
    ("Ipoh - Butterworth", "Not applicable"): [
        "timetables/utara_ipoh_1.parquet",
        "timetables/utara_ipoh_2.parquet",
    ],
}

# --- HEADER ---
st.markdown("""
<div style="text-align: center; padding: 0.5rem 1rem;">
    <h1 style="color:#2563eb; font-size:1.8rem; margin:0; font-weight:700;">
        🚆 KTM <span style="color:#fbbf24;">Schedule</span>
    </h1>
    <p style="color:#6b7280; font-size:0.9rem; margin:0.25rem 0;">
        Check KTMB train schedules across Malaysia
    </p>
</div>
""", unsafe_allow_html=True)


# --- INPUTS ---


with st.expander("🎯 Select Journey", expanded=True):

    col1, col2 = st.columns([2, 1])

    routes = [
        "Batu Caves - Pulau Sebang",
        "Tanjung Malim - Pelabuhan Klang",
        "Padang Besar - Butterworth",
        "Ipoh - Butterworth"
    ]

    with col1:
        selected_route = st.selectbox("Route", ["Select a route"] + routes)

    with col2:
        if selected_route in ["Padang Besar - Butterworth", "Ipoh - Butterworth"]:
            selected_schedule = "Not applicable"
            st.selectbox("Schedule Type", ["Not applicable"], disabled=True)
        else:
            selected_schedule = st.selectbox("Schedule Type", ["Select schedule type", "Weekdays", "Weekends"])

    # --- STATIONS ---
    if selected_route != "Select a route":
        key = (selected_route, selected_schedule)
        if key in file_map:
            try:
                df = load_parquet(file_map[key][0])
                station_list = sorted(df["STATION"].dropna().unique())
            except Exception:
                st.error("⚠️ Could not load station list.")
                st.stop()

            # --- Station Selection ---
            st.markdown("### 🎯 Select Stations")
            col1, col2 = st.columns(2)
            departure = col1.selectbox("From", ["Select departure"] + station_list)
            destination = col2.selectbox("To", ["Select destination"] + station_list)

            # --- TIME FILTER ---
            st.caption(f"⏰ Current time: **{time_depart.strftime('%I:%M %p')}**")
            use_custom_time = st.checkbox("Show past schedules / choose custom time")
            if use_custom_time:
                time_depart = st.slider("Select departure time", value=time_depart, step=timedelta(minutes=15))
                filter_minutes = time_depart.hour * 60 + time_depart.minute
            else:
                filter_minutes = kl_time.hour * 60 + kl_time.minute  # filter by *current* KL time

# --- DISPLAY RESULT ---
if selected_route != "Select a route":
    if 'departure' in locals() and 'destination' in locals():
        if departure != "Select departure" and destination != "Select destination":
            if departure == destination:
                st.warning("📍 Departure and destination cannot be the same.")
            else:
                st.markdown(f"""
                    <div style="background:#e6f7ff; padding:12px; border-radius:8px; border-left:5px solid #1f77b4; text-align:center;">
                        <h3 style="color:#1f77b4; margin:0;">🚆 {departure} → {destination}</h3>
                    </div>
                """, unsafe_allow_html=True)

                with st.spinner("🕒 Loading schedule..."):
                    schedule_df = get_train_schedules(
                        file_map, selected_route, selected_schedule,
                        departure, destination, filter_time=filter_minutes
                    )
                    if not schedule_df.empty:
                        try:
                            # --- Find the next train ---
                            schedule_df["Dep_Minutes"] = schedule_df["Departure_Time"].apply(parse_time_to_minutes)
                            next_train_idx = schedule_df["Dep_Minutes"].idxmin()

                            def highlight_next(row):
                                return ['background-color: #d1fae5; font-weight: bold;' if row.name == next_train_idx else '' for _ in row]

                            styled_df = (
                                schedule_df.drop(columns=["Dep_Minutes"])
                                .style
                                .apply(highlight_next, axis=1)
                                .hide(axis="index")   # 🔹 Hide index
                                .set_table_styles([   # 🔹 Bold header
                                    {'selector': 'th',
                                    'props': [('font-weight', 'bold'),
                                            ('background-color', '#f9fafb')]}
                                ])
                                .set_properties(      # 🔹 Center align Departure & Arrival
                                    subset=["Departure_Time", "Arrival_Time"],
                                    **{'text-align': 'center'}
                                )
                            )

                            st.dataframe(styled_df, use_container_width=True, height=400)
                            st.success(f"✅ Next available train: **{schedule_df.loc[next_train_idx, 'Departure_Time']}** from {departure}")
                        except Exception:
                            st.dataframe(schedule_df, use_container_width=True, height=400)
                    else:
                        st.info("📭 No upcoming train schedule found.")

else:
    st.info("🚆 Please select a route to begin.")

# --- FOOTER ---
st.markdown("---")
st.markdown("<p style='text-align:center; font-size:0.8rem; color:#6b7280;'>Created by: ubaid</p>", unsafe_allow_html=True)










# with st.expander("🎯 Select Journey", expanded=True):

#     col1, col2 = st.columns([2, 1])

#     routes = [
#         "Batu Caves - Pulau Sebang",
#         "Tanjung Malim - Pelabuhan Klang",
#         "Padang Besar - Butterworth",
#         "Ipoh - Butterworth"
#     ]

#     with col1:
#         selected_route = st.selectbox("Route", ["Select a route"] + routes)

#     with col2:
#         if selected_route in ["Padang Besar - Butterworth", "Ipoh - Butterworth"]:
#             selected_schedule = "Not applicable"
#             st.selectbox("Schedule Type", ["Not applicable"], disabled=True)
#         else:
#             selected_schedule = st.selectbox("Schedule Type", ["Select schedule type", "Weekdays", "Weekends"])


# # --- STATIONS ---
# if selected_route != "Select a route":
#     key = (selected_route, selected_schedule)
#     if key in file_map:
#         try:
#             df = load_parquet(file_map[key][0])
#             station_list = sorted(df["STATION"].dropna().unique())
#         except Exception:
#             st.error("⚠️ Could not load station list.")
#             st.stop()


#         # --- Station Selection ---
#         st.markdown("### 🎯 Select Stations")
#         col1, col2 = st.columns(2)
#         departure = col1.selectbox("From", ["Select departure"] + station_list)
#         destination = col2.selectbox("To", ["Select destination"] + station_list)

#         # --- TIME FILTER ---
#         st.caption(f"⏰ Current time: **{time_depart.strftime('%I:%M %p')}**")
#         use_custom_time = st.checkbox("Show past schedules / choose custom time")
#         if use_custom_time:
#             time_depart = st.slider("Select departure time", value=time_depart, step=timedelta(minutes=15))
#             filter_minutes = time_depart.hour * 60 + time_depart.minute
#         else:
#             filter_minutes = kl_time.hour * 60 + kl_time.minute  # filter by *current* KL time

#         # --- DISPLAY RESULT ---
#         if departure != "Select departure" and destination != "Select destination":
#             if departure == destination:
#                 st.warning("📍 Departure and destination cannot be the same.")
#             else:
#                 st.markdown(f"""
#                     <div style="background:#e6f7ff; padding:12px; border-radius:8px; border-left:5px solid #1f77b4; text-align:center;">
#                         <h3 style="color:#1f77b4; margin:0;">🚆 {departure} → {destination}</h3>
#                     </div>
#                 """, unsafe_allow_html=True)

#                 with st.spinner("🕒 Loading schedule..."):
#                     schedule_df = get_train_schedules(
#                         file_map, selected_route, selected_schedule,
#                         departure, destination, filter_time=filter_minutes
#                     )
#                     if not schedule_df.empty:
#                         try:
#                             # --- Find the next train ---
#                             schedule_df["Dep_Minutes"] = schedule_df["Departure_Time"].apply(parse_time_to_minutes)
#                             next_train_idx = schedule_df["Dep_Minutes"].idxmin()

#                             def highlight_next(row):
#                                 return ['background-color: #d1fae5; font-weight: bold;' if row.name == next_train_idx else '' for _ in row]

#                             styled_df = (
#                                 schedule_df.drop(columns=["Dep_Minutes"])
#                                 .style
#                                 .apply(highlight_next, axis=1)
#                                 .hide(axis="index")   # 🔹 Hide index
#                                 .set_table_styles([   # 🔹 Bold header
#                                     {'selector': 'th',
#                                     'props': [('font-weight', 'bold'),
#                                             ('background-color', '#f9fafb')]}
#                                 ])
#                                 .set_properties(      # 🔹 Center align Departure & Arrival
#                                     subset=["Departure_Time", "Arrival_Time"],
#                                     **{'text-align': 'center'}
#                                 )
#                             )

#                             st.dataframe(styled_df, use_container_width=True, height=400)
#                             st.success(f"✅ Next available train: **{schedule_df.loc[next_train_idx, 'Departure_Time']}** from {departure}")
#                         except Exception:
#                             st.dataframe(schedule_df, use_container_width=True, height=400)
#                     else:
#                         st.info("📭 No upcoming train schedule found.")



# else:
#     st.info("🚆 Please select a route to begin.")

# # --- FOOTER ---
# st.markdown("---")
# st.markdown("<p style='text-align:center; font-size:0.8rem; color:#6b7280;'>Created by: ubaid</p>", unsafe_allow_html=True)
