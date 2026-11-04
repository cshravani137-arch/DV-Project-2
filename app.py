import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="EV Charging Story", layout="wide")


@st.cache_data
def load():
    df = pd.read_csv("ev_charging_sessions.csv", parse_dates=["Session Date"])
    df["Month"] = df["Session Date"].dt.to_period("M").astype(str)
    df["Weekday"] = df["Session Date"].dt.day_name()
    return df


df = load()

st.sidebar.title("EV CHARGING STORY")
page = st.sidebar.radio("Dashboard", ["Overview", "Station & Vehicle Insights", "Wait & Charging Performance",
                                      "User Ratings", "Payments & Value"])

st.sidebar.header("Filters")
dr = st.sidebar.date_input("Date range", [df["Session Date"].min(), df["Session Date"].max()])
if len(dr) != 2:
    st.info("Select both a start date and an end date.")
    st.stop()
d1, d2 = dr
cities = st.sidebar.multiselect("City", sorted(df["City"].unique()), default=sorted(df["City"].unique()))
stations = st.sidebar.multiselect("Station Type", sorted(df["Station Type"].unique()),
                                  default=sorted(df["Station Type"].unique()))
pays = st.sidebar.multiselect("Payment Mode", sorted(df["Payment Mode"].unique()),
                              default=sorted(df["Payment Mode"].unique()))

f = df[(df["Session Date"] >= pd.to_datetime(d1)) & (df["Session Date"] <= pd.to_datetime(d2))
       & df["City"].isin(cities) & df["Station Type"].isin(stations) & df["Payment Mode"].isin(pays)]

if f.empty:
    st.warning("No data for the selected filters.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Sessions", f"{len(f):,}")
c2.metric("Total Revenue", f"Rs. {f['Charging Cost'].sum() / 1e5:.1f}L")
c3.metric("Avg Wait Time", f"{f['Wait Time (min)'].mean():.1f} min")
c4.metric("Avg Rating", f"{f['Rating'].mean():.2f} / 5")
st.divider()

left, right = st.columns([3, 2])

if page == "Overview":
    st.header("EV Charging | Executive Overview")
    m = f.groupby("Month").size().reset_index(name="Sessions")
    left.plotly_chart(px.line(m, x="Month", y="Sessions", markers=True, title="1. Sessions per month"),
                      use_container_width=True)
    c = f.groupby("City").size().reset_index(name="Sessions").sort_values("Sessions")
    right.plotly_chart(px.bar(c, x="Sessions", y="City", orientation="h", title="2. Sessions by city"),
                       use_container_width=True)
    top = c.iloc[-1]
    st.info(f"STORY 01 | Sessions peak in a few months and are concentrated in a few cities. "
            f"In this view {top['City']} leads with {top['Sessions']} sessions "
            f"({top['Sessions'] / len(f):.1%}).")

elif page == "Station & Vehicle Insights":
    st.header("Station & Vehicle Insights | What Earns and Who Charges?")
    r = f.groupby("Station Type")["Charging Cost"].sum().reset_index().sort_values("Charging Cost")
    left.plotly_chart(px.bar(r, x="Charging Cost", y="Station Type", orientation="h",
                             title="1. Revenue by station type"), use_container_width=True)
    e = f.groupby("Vehicle Type")["Energy (kWh)"].mean().reset_index().sort_values("Energy (kWh)")
    right.plotly_chart(px.bar(e, x="Energy (kWh)", y="Vehicle Type", orientation="h",
                              title="2. Average energy per session by vehicle"), use_container_width=True)
    top = r.iloc[-1]
    st.info(f"STORY 02 | Revenue depends on energy delivered and station price, not only on session count. "
            f"In this view {top['Station Type']} earns the most (Rs. {top['Charging Cost']:,.0f}).")

elif page == "Wait & Charging Performance":
    st.header("Wait & Charging Performance | How Long Do Drivers Wait?")
    left.plotly_chart(px.histogram(f, x="Wait Time (min)", nbins=18, title="1. Distribution of wait time"),
                      use_container_width=True)
    d = f.groupby("City")["Wait Time (min)"].mean().reset_index().sort_values("Wait Time (min)")
    right.plotly_chart(px.bar(d, x="Wait Time (min)", y="City", orientation="h",
                              title="2. Avg wait time by city"), use_container_width=True)
    slow = (f["Wait Time (min)"] > 20).mean()
    st.info(f"STORY 03 | Waiting varies by city, and a long tail of slow sessions exists. "
            f"In this view {slow:.1%} of sessions waited more than 20 minutes.")

elif page == "User Ratings":
    st.header("User Ratings | What Drives Satisfaction?")
    rd = f["Rating"].round().astype(int).value_counts().sort_index().reset_index()
    rd.columns = ["Rating", "Sessions"]
    left.plotly_chart(px.bar(rd, x="Rating", y="Sessions", title="1. Rating distribution"),
                      use_container_width=True)
    f = f.assign(Bucket=pd.cut(f["Wait Time (min)"], [-1, 5, 10, 20, 30, 100],
                               labels=["<=5", "6-10", "11-20", "21-30", "30+"]))
    b = f.groupby("Bucket", observed=True)["Rating"].mean().reset_index()
    right.plotly_chart(px.line(b, x="Bucket", y="Rating", markers=True, title="2. Avg rating by wait time"),
                       use_container_width=True)
    corr = f["Wait Time (min)"].corr(f["Rating"])
    st.info(f"STORY 04 | Shorter waits earn clearly higher ratings. "
            f"In this view the correlation between wait time and rating is {corr:.2f}.")

else:
    st.header("Payments & Value | How Do Drivers Pay?")
    p = f["Payment Mode"].value_counts().reset_index()
    p.columns = ["Payment Mode", "Sessions"]
    left.plotly_chart(px.pie(p, names="Payment Mode", values="Sessions", title="1. Payment mode share"),
                      use_container_width=True)
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    w = f.groupby("Weekday")["Charging Cost"].mean().reindex(order).reset_index()
    right.plotly_chart(px.bar(w, x="Weekday", y="Charging Cost", title="2. Avg charging cost by weekday"),
                       use_container_width=True)
    st.info(f"STORY 05 | UPI and other digital modes dominate, and charging cost shifts by day of week. "
            f"In this view {p.iloc[0]['Payment Mode']} is the leading mode "
            f"({p.iloc[0]['Sessions'] / len(f):.1%}).")

st.download_button("Download filtered data (CSV)", f.to_csv(index=False), "filtered_sessions.csv", "text/csv")
