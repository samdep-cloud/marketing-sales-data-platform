import os
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
from pyathena import connect

load_dotenv()
ATHENA_RESULTS = os.environ["ATHENA_RESULTS_S3"]

st.set_page_config(
    page_title="Marketing & Sales Data Platform",
    layout="wide"
)

st.title("Marketing & Sales Data Platform")
st.caption("AWS S3 | Glue | Athena | Streamlit")

@st.cache_data(ttl=300)
def load_bookings():
    conn = connect(
        region_name="us-east-1",
        schema_name="marketing_sales",
        s3_staging_dir=ATHENA_RESULTS
    )

    query = """
        SELECT meeting_date, total_bookings
        FROM marketing_sales.gold_daily_bookings
        ORDER BY meeting_date
    """

    with conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

    return pd.DataFrame(rows, columns=columns)


@st.cache_data(ttl=300)
def load_funnel_conversions():
    conn = connect(
        region_name="us-east-1",
        schema_name="marketing_sales",
        s3_staging_dir=ATHENA_RESULTS
    )

    query = """
        SELECT
            funnel,
            total_leads,
            booked_leads,
            booking_rate_pct
        FROM marketing_sales.gold_funnel_conversions
        ORDER BY total_leads DESC
    """

    with conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

    return pd.DataFrame(rows, columns=columns)

@st.cache_data(ttl=300)
def load_employee_workload():
    conn = connect(
        region_name="us-east-1",
        schema_name="marketing_sales",
        s3_staging_dir=ATHENA_RESULTS
    )

    query = """
        SELECT
            employee_name,
            total_meetings,
            scheduled_hours
        FROM marketing_sales.gold_employee_workload
        ORDER BY total_meetings DESC
    """

    with conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

    return pd.DataFrame(rows, columns=columns)

@st.cache_data(ttl=300)
def load_ad_spend():
    conn = connect(
        region_name="us-east-1",
        schema_name="marketing_sales",
        s3_staging_dir=ATHENA_RESULTS
    )

    query = """
        SELECT
            date,
            channel,
            SUM(spend) AS total_spend
        FROM marketing_sales.spend
        GROUP BY date, channel
        ORDER BY date
    """

    with conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

    return pd.DataFrame(rows, columns=columns)

try:
    df = load_bookings()

    st.subheader("Daily Bookings")

    if not df.empty:
        df["meeting_date"] = pd.to_datetime(df["meeting_date"])
        df["total_bookings"] = pd.to_numeric(df["total_bookings"])

        st.metric("Total Bookings", f"{df['total_bookings'].sum():,}")

        st.line_chart(
            df.set_index("meeting_date")["total_bookings"]
        )

        with st.expander("View underlying data"):
            st.dataframe(df, use_container_width=True)
    else:
        st.info("No booking data available.")


    st.divider()
    st.subheader("Lead-to-Booking Funnel Conversions")

    funnel_df = load_funnel_conversions()

    if not funnel_df.empty:
        for col in ["total_leads", "booked_leads", "booking_rate_pct"]:
            funnel_df[col] = pd.to_numeric(funnel_df[col])

        total_leads = int(funnel_df["total_leads"].sum())
        booked_leads = int(funnel_df["booked_leads"].sum())
        conversion_rate = (
            100 * booked_leads / total_leads if total_leads else 0
        )

        col1, col2, col3 = st.columns(3)

        col1.metric("Unique Leads", f"{total_leads:,}")
        col2.metric("Leads with Bookings", f"{booked_leads:,}")
        col3.metric("Observed Booking Rate", f"{conversion_rate:.1f}%")

        st.bar_chart(
            funnel_df.set_index("funnel")["booking_rate_pct"],
            y_label="Booking Rate (%)"
        )

        with st.expander("View funnel details"):
            st.dataframe(funnel_df, use_container_width=True)
    else:
        st.info("No funnel conversion data available.")


    st.divider()
    st.subheader("Employee Meeting Workload")

    workload_df = load_employee_workload()

    if not workload_df.empty:
        workload_df["total_meetings"] = pd.to_numeric(
            workload_df["total_meetings"]
        )
        workload_df["scheduled_hours"] = pd.to_numeric(
            workload_df["scheduled_hours"]
        )

        st.bar_chart(
            workload_df.set_index("employee_name")["total_meetings"],
            y_label="Scheduled Meetings"
        )

        with st.expander("View employee workload details"):
            st.dataframe(workload_df, use_container_width=True)
    else:
        st.info("No employee workload data available.")


    st.divider()
    st.subheader("Advertising Spend")

    spend_df = load_ad_spend()

    if not spend_df.empty:
        spend_df["date"] = pd.to_datetime(spend_df["date"])
        spend_df["total_spend"] = pd.to_numeric(
            spend_df["total_spend"]
        )

        st.metric(
            "Total Ad Spend",
            f"${spend_df['total_spend'].sum():,.2f}"
        )

        daily_spend = (
            spend_df.groupby("date")["total_spend"]
            .sum()
            .sort_index()
        )

        st.bar_chart(
            daily_spend,
            x_label="Date",
            y_label="Daily Spend ($)"
        )

        st.caption("Spend by Channel")

        channel_spend = (
            spend_df.groupby("channel")["total_spend"]
            .sum()
            .sort_values(ascending=False)
        )

        st.bar_chart(
            channel_spend,
            y_label="Total Spend ($)"
        )
    else:
        st.info("No advertising spend data available.")


    st.divider()
    st.subheader("Lead Acquisition by Funnel")

    if not funnel_df.empty:
        acquisition_df = funnel_df.copy()

        acquisition_df["lead_share_pct"] = (
            100 * acquisition_df["total_leads"]
            / acquisition_df["total_leads"].sum()
        ).round(1)

        st.bar_chart(
            acquisition_df.set_index("funnel")["total_leads"],
            y_label="Unique Leads"
        )

        st.dataframe(
            acquisition_df[
                [
                    "funnel",
                    "total_leads",
                    "lead_share_pct",
                    "booked_leads",
                    "booking_rate_pct"
                ]
            ].rename(columns={
                "funnel": "Funnel",
                "total_leads": "Unique Leads",
                "lead_share_pct": "Share of Leads (%)",
                "booked_leads": "Leads with Bookings",
                "booking_rate_pct": "Booking Rate (%)"
            }),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No lead acquisition data available.")

except Exception as e:
    st.error(f"Athena query failed: {e}")
