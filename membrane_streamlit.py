import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from membrane_app import (
    simulate_membrane_configuration,
    run_base_case_comparison,
    sensitivity_feed_co2,
    sensitivity_electricity_price,
    sensitivity_feed_flow,
    RESULTS_DIR
)

st.set_page_config(layout="wide", page_title="Membrane biogas upgrading")

st.title("Simplified membrane-based biogas upgrading")

with st.sidebar:
    st.header("Inputs")
    feed_flow = st.number_input("Feed flow (Nm3/h)", value=300.0, min_value=1.0)
    feed_ch4 = st.slider("Feed CH4 (%)", min_value=0.0, max_value=100.0, value=60.0)
    feed_co2 = st.slider("Feed CO2 (%)", min_value=0.0, max_value=100.0, value=40.0)
    electricity_price = st.number_input("Electricity price ($/kWh)", value=0.07, format="%.4f")
    config = st.selectbox("Configuration", options=["all", "single_stage", "two_stage", "three_stage"])
    run_sens = st.checkbox("Run sensitivities (three_stage)", value=False)
    run_button = st.button("Run model")

if run_button:
    try:
        if config == "all":
            df = run_base_case_comparison(feed_flow, feed_ch4, feed_co2, electricity_price)
        else:
            res = simulate_membrane_configuration(feed_flow, feed_ch4, feed_co2, config, electricity_price)
            df = pd.DataFrame([res])

        st.subheader("Base case results")
        st.dataframe(df.round(4))

        # save results csv
        RESULTS_DIR.mkdir(exist_ok=True)
        out_csv = RESULTS_DIR / "streamlit_base_case.csv"
        df.to_csv(out_csv, index=False)
        st.success(f"Results saved to {out_csv}")

        # quick plot: CH4 purity by configuration
        fig, ax = plt.subplots()
        ax.bar(df["configuration"], df["biomethane_CH4_percent"])
        ax.set_ylabel("Biomethane CH4 purity (%)")
        ax.set_title("CH4 purity comparison")
        st.pyplot(fig)

        if run_sens:
            st.subheader("Sensitivities (three_stage)")
            s1 = sensitivity_feed_co2(configuration_name="three_stage", feed_flow_nm3_h=feed_flow, electricity_price=electricity_price)
            st.write("Feed CO2 sensitivity")
            st.dataframe(s1.round(4))
            s1.to_csv(RESULTS_DIR / "streamlit_sensitivity_feed_co2.csv", index=False)

            s2 = sensitivity_electricity_price(configuration_name="three_stage", feed_flow_nm3_h=feed_flow)
            st.write("Electricity price sensitivity")
            st.dataframe(s2[["electricity_price", "specific_cost_per_MWh", "annual_electricity_cost"]].round(4))
            s2.to_csv(RESULTS_DIR / "streamlit_sensitivity_electricity.csv", index=False)

            s3 = sensitivity_feed_flow(configuration_name="three_stage", electricity_price=electricity_price)
            st.write("Feed flow sensitivity")
            st.dataframe(s3[["feed_flow_Nm3_h", "annual_biomethane_Nm3", "specific_cost_per_MWh"]].round(4))
            s3.to_csv(RESULTS_DIR / "streamlit_sensitivity_feed_flow.csv", index=False)

            st.success("Sensitivities computed and saved.")
    except Exception as e:
        st.error(f"Error: {e}")
