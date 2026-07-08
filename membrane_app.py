# -*- coding: utf-8 -*-
"""
Simplified membrane-based biogas upgrading model

Project:
Simplified process and techno-economic screening of polyimide membrane
biogas upgrading.

This is a simplified model inspired mainly by P8 and supported by P9.
It does NOT reproduce Aspen HYSYS / ChemBrane.
It uses transparent mass balances and configuration-level assumptions.

Author: Your name
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# 1. PROJECT FOLDERS
# ============================================================

try:
    SCRIPT_DIR = Path(__file__).resolve().parent
except NameError:
    SCRIPT_DIR = Path.cwd()

# If the script is inside /scripts, project folder is one level above
if SCRIPT_DIR.name.lower() == "scripts":
    PROJECT_DIR = SCRIPT_DIR.parent
else:
    PROJECT_DIR = SCRIPT_DIR

RESULTS_DIR = PROJECT_DIR / "results"
FIGURES_DIR = PROJECT_DIR / "figures"

RESULTS_DIR.mkdir(exist_ok=True)
FIGURES_DIR.mkdir(exist_ok=True)


# ============================================================
# 2. BASE INPUT DATA
# ============================================================

# Base case inspired by P8
FEED_FLOW_NM3_H = 300.0
FEED_CH4_PERCENT = 60.0
FEED_CO2_PERCENT = 40.0

# Operating and economic assumptions
OPERATING_HOURS_PER_YEAR = 8200
SPECIFIC_ENERGY_KWH_PER_NM3_FEED = 0.25

ELECTRICITY_PRICE = 0.07       # $/kWh, close to P8 value
BIOMETHANE_PRICE = 0.80        # $/Nm3 biomethane, from P8 assumption
BIOMETHANE_ENERGY_KWH_NM3 = 10.0

PLANT_LIFETIME_YEARS = 15
DISCOUNT_RATE = 0.10

# Simplified total membrane upgrading CAPEX factor.
# P9 gives membrane CAPEX logic around 3260 per m3/h capacity.
CAPEX_PER_NM3_H_CAPACITY = 3260.0

OPEX_FRACTION_OF_CAPEX = 0.03


# ============================================================
# 3. MEMBRANE CONFIGURATION ASSUMPTIONS
# ============================================================
"""
These are simplified configuration-level assumptions.

The values are not exact membrane physics.
They represent the expected trend from P8:

- Single-stage polyimide: simple, but low CH4 recovery.
- Two-stage polyimide: better recovery, but recycle/compression problems.
- Three-stage polyimide: best polymeric option in P8.

ch4_to_product_fraction:
    fraction of feed CH4 ending in biomethane product.

co2_to_product_fraction:
    fraction of feed CO2 remaining in biomethane product.
    The rest is removed to CO2-rich off-gas.

specific_energy:
    simplified energy use, kWh/Nm3 raw biogas.
"""

CONFIGURATIONS = {
    "single_stage": {
        "description": "Single-stage polyimide membrane",
        "ch4_to_product_fraction": 0.83,
        "co2_to_product_fraction": 0.025,
        "specific_energy": 0.20,
        "capex_multiplier": 0.85
    },
    "two_stage": {
        "description": "Two-stage polyimide membrane",
        "ch4_to_product_fraction": 0.96,
        "co2_to_product_fraction": 0.035,
        "specific_energy": 0.38,
        "capex_multiplier": 1.10
    },
    "three_stage": {
        "description": "Simplified three-stage polyimide membrane",
        "ch4_to_product_fraction": 0.995,
        "co2_to_product_fraction": 0.03825,
        "specific_energy": 0.28,
        "capex_multiplier": 1.25
    }
}


# ============================================================
# 4. BASIC CALCULATION FUNCTIONS
# ============================================================

def capital_recovery_factor(rate, years):
    """
    Calculates capital recovery factor.
    """
    if rate == 0:
        return 1 / years

    return (rate * (1 + rate) ** years) / ((1 + rate) ** years - 1)


def validate_feed(ch4_percent, co2_percent):
    """
    Checks that CH4 + CO2 = 100%.
    """
    total = ch4_percent + co2_percent

    if abs(total - 100.0) > 1e-6:
        raise ValueError(
            f"Feed composition must sum to 100%. Current total = {total}"
        )


def simulate_membrane_configuration(
    feed_flow_nm3_h,
    feed_ch4_percent,
    feed_co2_percent,
    configuration_name,
    electricity_price=ELECTRICITY_PRICE
):
    """
    Simulates one membrane configuration using simplified mass balances.
    """

    validate_feed(feed_ch4_percent, feed_co2_percent)

    if configuration_name not in CONFIGURATIONS:
        raise ValueError(f"Unknown configuration: {configuration_name}")

    config = CONFIGURATIONS[configuration_name]

    # Feed component flows
    ch4_feed = feed_flow_nm3_h * feed_ch4_percent / 100.0
    co2_feed = feed_flow_nm3_h * feed_co2_percent / 100.0

    # Product component flows
    ch4_product = ch4_feed * config["ch4_to_product_fraction"]
    co2_product = co2_feed * config["co2_to_product_fraction"]

    # Off-gas component flows
    ch4_offgas = ch4_feed - ch4_product
    co2_offgas = co2_feed - co2_product

    # Total flows
    product_flow = ch4_product + co2_product
    offgas_flow = ch4_offgas + co2_offgas

    # Avoid division by zero
    if product_flow <= 0:
        ch4_purity = 0
        co2_product_percent = 0
    else:
        ch4_purity = 100.0 * ch4_product / product_flow
        co2_product_percent = 100.0 * co2_product / product_flow

    if offgas_flow <= 0:
        offgas_ch4_percent = 0
        offgas_co2_percent = 0
    else:
        offgas_ch4_percent = 100.0 * ch4_offgas / offgas_flow
        offgas_co2_percent = 100.0 * co2_offgas / offgas_flow

    # Performance indicators
    ch4_recovery = 100.0 * ch4_product / ch4_feed
    methane_slip = 100.0 * ch4_offgas / ch4_feed
    co2_removal = 100.0 * co2_offgas / co2_feed

    # Energy and annual production
    specific_energy = config["specific_energy"]

    annual_raw_biogas = feed_flow_nm3_h * OPERATING_HOURS_PER_YEAR
    annual_biomethane = product_flow * OPERATING_HOURS_PER_YEAR

    annual_electricity_kwh = (
        feed_flow_nm3_h
        * specific_energy
        * OPERATING_HOURS_PER_YEAR
    )

    annual_electricity_cost = annual_electricity_kwh * electricity_price

    annual_biomethane_energy_mwh = (
        annual_biomethane
        * BIOMETHANE_ENERGY_KWH_NM3
        / 1000.0
    )

    # Simplified CAPEX/OPEX
    capex = (
        CAPEX_PER_NM3_H_CAPACITY
        * feed_flow_nm3_h
        * config["capex_multiplier"]
    )

    crf = capital_recovery_factor(DISCOUNT_RATE, PLANT_LIFETIME_YEARS)
    annualized_capex = capex * crf

    annual_opex = capex * OPEX_FRACTION_OF_CAPEX

    total_annual_cost = (
        annualized_capex
        + annual_opex
        + annual_electricity_cost
    )

    if annual_biomethane > 0:
        specific_cost_per_nm3 = total_annual_cost / annual_biomethane
    else:
        specific_cost_per_nm3 = np.nan

    if annual_biomethane_energy_mwh > 0:
        specific_cost_per_mwh = total_annual_cost / annual_biomethane_energy_mwh
    else:
        specific_cost_per_mwh = np.nan

    annual_revenue = annual_biomethane * BIOMETHANE_PRICE

    annual_cash_before_capex = (
        annual_revenue
        - annual_opex
        - annual_electricity_cost
    )

    if annual_cash_before_capex > 0:
        simple_payback_years = capex / annual_cash_before_capex
    else:
        simple_payback_years = np.nan

    result = {
        "configuration": configuration_name,
        "description": config["description"],

        "feed_flow_Nm3_h": feed_flow_nm3_h,
        "feed_CH4_percent": feed_ch4_percent,
        "feed_CO2_percent": feed_co2_percent,

        "CH4_feed_Nm3_h": ch4_feed,
        "CO2_feed_Nm3_h": co2_feed,

        "biomethane_flow_Nm3_h": product_flow,
        "biomethane_CH4_percent": ch4_purity,
        "biomethane_CO2_percent": co2_product_percent,

        "offgas_flow_Nm3_h": offgas_flow,
        "offgas_CH4_percent": offgas_ch4_percent,
        "offgas_CO2_percent": offgas_co2_percent,

        "CH4_recovery_percent": ch4_recovery,
        "methane_slip_percent": methane_slip,
        "CO2_removal_percent": co2_removal,

        "specific_energy_kWh_Nm3_feed": specific_energy,
        "annual_raw_biogas_Nm3": annual_raw_biogas,
        "annual_biomethane_Nm3": annual_biomethane,
        "annual_biomethane_energy_MWh": annual_biomethane_energy_mwh,
        "annual_electricity_kWh": annual_electricity_kwh,
        "annual_electricity_cost": annual_electricity_cost,

        "capex": capex,
        "annualized_capex": annualized_capex,
        "annual_opex": annual_opex,
        "total_annual_cost": total_annual_cost,
        "specific_cost_per_Nm3": specific_cost_per_nm3,
        "specific_cost_per_MWh": specific_cost_per_mwh,
        "annual_revenue": annual_revenue,
        "simple_payback_years": simple_payback_years
    }

    return result


# ============================================================
# 5. CASE COMPARISON
# ============================================================

def run_base_case_comparison():
    """
    Runs single-stage, two-stage and three-stage comparison.
    """
    results = []

    for config_name in CONFIGURATIONS:
        result = simulate_membrane_configuration(
            feed_flow_nm3_h=FEED_FLOW_NM3_H,
            feed_ch4_percent=FEED_CH4_PERCENT,
            feed_co2_percent=FEED_CO2_PERCENT,
            configuration_name=config_name
        )
        results.append(result)

    df = pd.DataFrame(results)
    return df


# ============================================================
# 6. SENSITIVITY ANALYSIS
# ============================================================

def sensitivity_feed_co2(configuration_name="three_stage"):
    """
    Changes CO2 content in feed from 30% to 50%.
    CH4 is adjusted so total remains 100%.
    """
    rows = []

    for co2_percent in [30, 35, 40, 45, 50]:
        ch4_percent = 100.0 - co2_percent

        result = simulate_membrane_configuration(
            feed_flow_nm3_h=FEED_FLOW_NM3_H,
            feed_ch4_percent=ch4_percent,
            feed_co2_percent=co2_percent,
            configuration_name=configuration_name
        )

        rows.append(result)

    return pd.DataFrame(rows)


def sensitivity_electricity_price(configuration_name="three_stage"):
    """
    Changes electricity price and calculates specific cost.
    """
    rows = []

    for price in np.linspace(0.05, 0.13, 9):
        result = simulate_membrane_configuration(
            feed_flow_nm3_h=FEED_FLOW_NM3_H,
            feed_ch4_percent=FEED_CH4_PERCENT,
            feed_co2_percent=FEED_CO2_PERCENT,
            configuration_name=configuration_name,
            electricity_price=price
        )

        result["electricity_price"] = price
        rows.append(result)

    return pd.DataFrame(rows)


def sensitivity_feed_flow(configuration_name="three_stage"):
    """
    Changes plant size / feed flowrate.
    """
    rows = []

    for flow in [100, 200, 300, 400, 500]:
        result = simulate_membrane_configuration(
            feed_flow_nm3_h=flow,
            feed_ch4_percent=FEED_CH4_PERCENT,
            feed_co2_percent=FEED_CO2_PERCENT,
            configuration_name=configuration_name
        )

        rows.append(result)

    return pd.DataFrame(rows)


# ============================================================
# 7. PLOT FUNCTIONS
# ============================================================

def save_bar_comparison(df):
    """
    Creates bar charts for configuration comparison.
    """

    plt.figure()
    plt.bar(df["configuration"], df["biomethane_CH4_percent"])
    plt.ylabel("Biomethane CH4 purity (%)")
    plt.title("CH4 purity comparison")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "comparison_ch4_purity.png", dpi=300)
    plt.show()

    plt.figure()
    plt.bar(df["configuration"], df["CH4_recovery_percent"])
    plt.ylabel("CH4 recovery (%)")
    plt.title("CH4 recovery comparison")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "comparison_ch4_recovery.png", dpi=300)
    plt.show()

    plt.figure()
    plt.bar(df["configuration"], df["specific_cost_per_MWh"])
    plt.ylabel("Specific cost ($/MWh biomethane)")
    plt.title("Specific cost comparison")
    plt.xticks(rotation=20)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "comparison_specific_cost.png", dpi=300)
    plt.show()


def plot_feed_co2_sensitivity(df):
    """
    Plots effect of feed CO2 on results.
    """

    plt.figure()
    plt.plot(df["feed_CO2_percent"], df["biomethane_CH4_percent"], marker="o")
    plt.xlabel("Feed CO2 content (%)")
    plt.ylabel("Biomethane CH4 purity (%)")
    plt.title("Effect of feed CO2 on biomethane purity")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "sensitivity_feed_co2_purity.png", dpi=300)
    plt.show()

    plt.figure()
    plt.plot(df["feed_CO2_percent"], df["specific_cost_per_MWh"], marker="o")
    plt.xlabel("Feed CO2 content (%)")
    plt.ylabel("Specific cost ($/MWh biomethane)")
    plt.title("Effect of feed CO2 on specific cost")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "sensitivity_feed_co2_cost.png", dpi=300)
    plt.show()


def plot_electricity_sensitivity(df):
    """
    Plots effect of electricity price on specific cost.
    """

    plt.figure()
    plt.plot(df["electricity_price"], df["specific_cost_per_MWh"], marker="o")
    plt.xlabel("Electricity price ($/kWh)")
    plt.ylabel("Specific cost ($/MWh biomethane)")
    plt.title("Effect of electricity price on biomethane cost")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "sensitivity_electricity_cost.png", dpi=300)
    plt.show()


def plot_feed_flow_sensitivity(df):
    """
    Plots effect of feed flowrate on specific cost.
    """

    plt.figure()
    plt.plot(df["feed_flow_Nm3_h"], df["specific_cost_per_MWh"], marker="o")
    plt.xlabel("Raw biogas feed flowrate (Nm3/h)")
    plt.ylabel("Specific cost ($/MWh biomethane)")
    plt.title("Effect of plant size on specific cost")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "sensitivity_feed_flow_cost.png", dpi=300)
    plt.show()


# ============================================================
# 8. MAIN RUN
# ============================================================

def main():
    print("\nStarting membrane biogas upgrading model...")
    print(f"Project folder: {PROJECT_DIR}")

    # --------------------------------------------------------
    # Base comparison
    # --------------------------------------------------------
    comparison_df = run_base_case_comparison()

    comparison_file = RESULTS_DIR / "base_case_configuration_comparison.csv"
    comparison_df.to_csv(comparison_file, index=False)

    selected_columns = [
        "configuration",
        "feed_flow_Nm3_h",
        "feed_CH4_percent",
        "feed_CO2_percent",
        "biomethane_flow_Nm3_h",
        "biomethane_CH4_percent",
        "CH4_recovery_percent",
        "methane_slip_percent",
        "CO2_removal_percent",
        "specific_cost_per_MWh",
        "simple_payback_years"
    ]

    print("\n=== Base case comparison ===")
    print(comparison_df[selected_columns].round(3).to_string(index=False))

    save_bar_comparison(comparison_df)

    # --------------------------------------------------------
    # Sensitivity: feed CO2 content
    # --------------------------------------------------------
    feed_co2_df = sensitivity_feed_co2(configuration_name="three_stage")
    feed_co2_file = RESULTS_DIR / "sensitivity_feed_co2_three_stage.csv"
    feed_co2_df.to_csv(feed_co2_file, index=False)

    print("\n=== Sensitivity: feed CO2 content, three-stage ===")
    print(feed_co2_df[selected_columns].round(3).to_string(index=False))

    plot_feed_co2_sensitivity(feed_co2_df)

    # --------------------------------------------------------
    # Sensitivity: electricity price
    # --------------------------------------------------------
    electricity_df = sensitivity_electricity_price(configuration_name="three_stage")
    electricity_file = RESULTS_DIR / "sensitivity_electricity_price_three_stage.csv"
    electricity_df.to_csv(electricity_file, index=False)

    print("\n=== Sensitivity: electricity price, three-stage ===")
    print(
        electricity_df[
            ["electricity_price", "specific_cost_per_MWh", "annual_electricity_cost"]
        ].round(3).to_string(index=False)
    )

    plot_electricity_sensitivity(electricity_df)

    # --------------------------------------------------------
    # Sensitivity: plant size / feed flowrate
    # --------------------------------------------------------
    feed_flow_df = sensitivity_feed_flow(configuration_name="three_stage")
    feed_flow_file = RESULTS_DIR / "sensitivity_feed_flow_three_stage.csv"
    feed_flow_df.to_csv(feed_flow_file, index=False)

    print("\n=== Sensitivity: feed flowrate, three-stage ===")
    print(
        feed_flow_df[
            ["feed_flow_Nm3_h", "annual_biomethane_Nm3", "specific_cost_per_MWh"]
        ].round(3).to_string(index=False)
    )

    plot_feed_flow_sensitivity(feed_flow_df)

    print("\nModel finished successfully.")
    print(f"Results saved in: {RESULTS_DIR}")
    print(f"Figures saved in: {FIGURES_DIR}")


if __name__ == "__main__":
    main()
