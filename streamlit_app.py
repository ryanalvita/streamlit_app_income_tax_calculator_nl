import streamlit as st
import numpy as np
import pandas as pd
import json
import plotly.graph_objects as go
import plotly.colors as co


# Functions
def clean_df(series):
    # Resample
    s = 1000
    l = (series.index.size - 1) * s + 1
    new_index = np.interp(np.arange(l), np.arange(l, step=s), series.index)
    series = series.reindex(index=new_index)

    # Interpolate
    series = series.interpolate()

    # Change type to int
    series.index = series.index.astype(int)
    series = series.astype(int)

    # Remove negative
    series = series[series >= 0]

    return series


def calculate_payroll_taxes(year, brackets):
    results = {0: 0}
    max_income = 120000
    year_brackets = brackets[year]
    for bracket in year_brackets:
        last_key = list(results.keys())[-1]
        if bracket.get("max"):
            results[bracket["max"] + 1] = (
                (bracket["max"] - bracket["min"]) + 1
            ) * bracket["rate"] + results[last_key]
        else:
            results[max_income] = max_income * bracket["rate"] + results[last_key]
    return clean_df(pd.Series(results))


def calculate_social_security_taxes(year, brackets, retire):
    results = {0: 0}
    max_income = 120000
    year_brackets = brackets[year]
    for bracket in year_brackets:
        tax_type = "older" if retire else "social"
        results[bracket["max"] + 1] = ((bracket["max"] - bracket["min"]) + 1) * bracket[
            tax_type
        ]
        results[max_income] = results[bracket["max"] + 1]
    return clean_df(pd.Series(results))


def calculate_general_tax_credits(year, brackets):
    results = {}
    max_income = 120000
    year_brackets = brackets[year]
    for bracket in year_brackets:
        if bracket.get("max"):
            if bracket["rate"] > 1:
                results[0] = bracket["rate"]
                results[bracket["max"] + 1] = bracket["rate"]
            else:
                results[bracket["max"] + 1] = 0
        else:
            results[max_income] = 0
    return clean_df(pd.Series(results))


def calculate_labour_tax_credits(year, brackets):
    results = {0: 0}
    max_income = 120000
    year_brackets = brackets[year]
    for bracket in year_brackets:
        last_key = list(results.keys())[-1]
        if bracket.get("max"):
            if bracket["rate"] > 1:
                results[bracket["max"] + 1] = bracket["rate"]
            else:
                results[bracket["max"] + 1] = (
                    (bracket["max"] - bracket["min"]) + 1
                ) * bracket["rate"] + results[last_key]
        else:
            results[max_income] = max_income * bracket["rate"] + results[last_key]
    return clean_df(pd.Series(results))


st.header("Income Tax Calculator - NL")
st.write("Calculate your basic income tax in the Netherlands in the most simple yet descriptive way")

with open("data.json", "r") as f:
    data = json.load(f)

years = reversed(data["years"].copy())

# Input section
col1, col2 = st.columns(2)
income = col1.number_input("Gross Yearly Income", min_value=0, value=60000, step=1000)
year = str(col2.selectbox("Tax Year", years, index=0))

retire = st.checkbox("Retire next year")

# Calculation
df_payroll_taxes = calculate_payroll_taxes(year, data["payrollTax"])
df_social_security_taxes = calculate_social_security_taxes(
    year, data["socialTax"], retire
)
df_general_tax_credits = calculate_general_tax_credits(year, data["generalCredit"])
df_labour_tax_credits = calculate_labour_tax_credits(year, data["labourCredit"])

df_dict = {
    "Payroll Tax": df_payroll_taxes,
    "Social Security Tax": df_social_security_taxes,
    "General Tax Credit": df_general_tax_credits,
    "Labour Tax Credit": df_labour_tax_credits,
}
payroll_tax = int(
    np.interp([income], df_payroll_taxes.index, df_payroll_taxes.values)[0]
)
social_security_tax = int(
    np.interp(
        [income], df_social_security_taxes.index, df_social_security_taxes.values
    )[0]
)
general_tax_credit = int(
    np.interp([income], df_general_tax_credits.index, df_general_tax_credits.values)[0]
)
labour_tax_credit = int(
    np.interp([income], df_labour_tax_credits.index, df_labour_tax_credits.values)[0]
)

# Table section
st.subheader("Table")
results = {
    "Income Before Tax": income,
    "Payroll Tax": payroll_tax,
    "Social Security Tax": social_security_tax,
    "General Tax Credit": general_tax_credit,
    "Labour Tax Credit": labour_tax_credit,
}

results["Income After Tax"] = (
    income
    - results["Payroll Tax"]
    - results["Social Security Tax"]
    + results["General Tax Credit"]
    + results["Labour Tax Credit"]
)

cols = st.columns([0.2, 0.6, 0.2])
series = pd.Series(results, name="Values")
cols[1].dataframe(series, use_container_width=True)
cols[1].markdown(
    """<div style="text-align: right; font-size: 0.75em">*values are per year</div>""",
    unsafe_allow_html=True,
)

# Graph section
st.subheader("Graph")
for key, values in df_dict.items():
    if not "Credit" in key:
        color = co.qualitative.Plotly[0]
    else:
        color = co.qualitative.Plotly[2]

    df = values
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df.values,
            mode="lines",
            name=f"{key}",
            line=dict(
                color=color,
                width=4,
            ),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[income],
            y=[results[key]],
            mode="markers",
            name=f"Your {key}",
            marker=dict(color=co.qualitative.Plotly[1], size=12),
        ),
    )
    fig.update_layout(
        title=f"{key}",
        legend={
            "orientation": "h",
        },
    )
    fig.update_yaxes(tickformat="~")
    st.plotly_chart(fig, use_container_width=True)

st.caption("**Disclamier:**")
st.caption(
    "This calculator provides an estimated income tax calculation based on the information provided. It is for illustrative purposes only and does not guarantee accuracy. Consult a tax professional for precise calculations."
)
