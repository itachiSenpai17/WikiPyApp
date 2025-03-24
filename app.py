# Install required packages
!pip install wikipedia wikipedia-api plotly

import urllib.parse
import datetime
import requests
import pandas as pd
from IPython.display import display, HTML
import plotly.graph_objects as go
import plotly.io as pio

# Set Plotly renderer for Colab
pio.renderers.default = "colab"

# ----------------------
# Step 1: User Input for URLs and Date Range
# ----------------------
url1 = input("Enter the first Wikipedia URL: ").strip()
url2 = input("Enter the second Wikipedia URL: ").strip()
start_date_str = input("Enter the start date (YYYY-MM-DD): ").strip()
end_date_str   = input("Enter the end date (YYYY-MM-DD): ").strip()

def extract_title(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.path.startswith("/wiki/"):
        return parsed.path.split("/wiki/")[1]
    else:
        raise ValueError("URL does not appear to be a valid Wikipedia article link.")

try:
    article1 = extract_title(url1)
    article2 = extract_title(url2)
except Exception as e:
    print("Error extracting article title:", e)
    raise

# Convert date strings to date objects and then into API format: YYYYMMDD00 (00 for hour)
try:
    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date   = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
except Exception as e:
    print("Error parsing dates:", e)
    raise

start_str = start_date.strftime("%Y%m%d") + "00"
end_str   = end_date.strftime("%Y%m%d") + "00"

# ----------------------
# Step 2: Helper Functions for API Query and Data Processing
# ----------------------
def get_pageviews(article, start_str, end_str):
    encoded_article = urllib.parse.quote(article, safe='')
    api_url = (
        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"en.wikipedia.org/all-access/all-agents/{encoded_article}/daily/{start_str}/{end_str}"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; ColabExample/1.0; +https://colab.research.google.com/)"
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("items", [])
    else:
        print(f"Failed to retrieve data for '{article}'. Status code: {response.status_code}")
        return []

def process_data(items, article_label):
    records = []
    for item in items:
        ts = item.get("timestamp", "")
        try:
            date = datetime.datetime.strptime(ts, "%Y%m%d%H").date()
        except Exception:
            date = None
        views = item.get("views", 0)
        records.append({"date": date, f"views_{article_label}": views})
    return pd.DataFrame(records)

# ----------------------
# Step 3: Retrieve and Process Data
# ----------------------
data1 = get_pageviews(article1, start_str, end_str)
data2 = get_pageviews(article2, start_str, end_str)

df1 = process_data(data1, article1)
df2 = process_data(data2, article2)

if df1.empty or df2.empty:
    print("One or both articles did not return pageview data.")
    raise SystemExit

# Merge the two DataFrames on 'date' and sort them
merged_df = pd.merge(df1, df2, on="date", how="outer")
merged_df.sort_values("date", inplace=True)

print("\nDaily pageview metrics (top 20 rows):")
display(HTML(merged_df.head(20).to_html(index=False)))

# ----------------------
# Step 4: Aggregate Data by Quarter
# ----------------------
merged_df['date'] = pd.to_datetime(merged_df['date'])
merged_df['quarter'] = merged_df['date'].dt.to_period('Q')
quarter_df = merged_df.groupby('quarter').agg({
    f'views_{article1}': 'mean',
    f'views_{article2}': 'mean'
}).reset_index().sort_values('quarter')
quarter_df['quarter_str'] = quarter_df['quarter'].apply(lambda r: f"Q{r.quarter} {r.year}")

print("\nQuarterly average daily views to be plotted:")
display(quarter_df[['quarter_str', f'views_{article1}', f'views_{article2}']])

# ----------------------
# Step 5: Plot the Data Using Plotly Graph Objects
# ----------------------
fig = go.Figure()

# Trace for the first article
fig.add_trace(go.Scatter(
    x=quarter_df['quarter_str'],
    y=quarter_df[f'views_{article1}'],
    mode='lines+markers',
    name=article1,
    marker=dict(color='red', size=8),
    line=dict(color='red', width=2)
))

# Trace for the second article
fig.add_trace(go.Scatter(
    x=quarter_df['quarter_str'],
    y=quarter_df[f'views_{article2}'],
    mode='lines+markers',
    name=article2,
    marker=dict(color='blue', size=8),
    line=dict(color='blue', width=2)
))

# Update layout for aesthetic appeal
fig.update_layout(
    title={
        'text': "<b>Average Daily Wikipedia Pageviews by Quarter</b>",
        'x': 0.5,
        'xanchor': 'center',
        'yanchor': 'top',
        'font': dict(size=24, color='black', family="Arial")
    },
    xaxis=dict(
        title='Quarter',
        titlefont=dict(size=16, color='black', family="Arial"),
        tickfont=dict(size=12, color='black', family="Arial"),
        showline=True,
        linewidth=2,
        linecolor='black',
        gridcolor='lightgray'
    ),
    yaxis=dict(
        title='Average Daily Views',
        titlefont=dict(size=16, color='black', family="Arial"),
        tickfont=dict(size=12, color='black', family="Arial"),
        showline=True,
        linewidth=2,
        linecolor='black',
        gridcolor='lightgray'
    ),
    plot_bgcolor='aliceblue',
    paper_bgcolor='lavender',
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=12, color='black', family="Arial")
    ),
    hovermode="x unified"
)

fig.show(renderer="colab")
