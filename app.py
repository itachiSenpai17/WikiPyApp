# Install required packages
!pip install gradio wikipedia wikipedia-api plotly

import urllib.parse
import datetime
import requests
import pandas as pd
import plotly.graph_objects as go
import gradio as gr

# --- Helper Functions ---
def extract_title(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.path.startswith("/wiki/"):
        return parsed.path.split("/wiki/")[1]
    else:
        raise ValueError("Invalid Wikipedia URL")

def get_pageviews(article, start_str, end_str):
    encoded_article = urllib.parse.quote(article, safe='')
    url = (
        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"en.wikipedia.org/all-access/all-agents/{encoded_article}/daily/{start_str}/{end_str}"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; GradioApp/1.0; +https://gradio.app)"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("items", [])
    return []

def process_data(items, article_label):
    records = []
    for item in items:
        ts = item.get("timestamp", "")
        try:
            date = datetime.datetime.strptime(ts, "%Y%m%d%H").date()
        except:
            date = None
        views = item.get("views", 0)
        records.append({"date": date, f"views_{article_label}": views})
    return pd.DataFrame(records)

# --- Main App Logic ---
def analyze_wiki(url1, url2, start_date_str, end_date_str):
    try:
        article1 = extract_title(url1)
        article2 = extract_title(url2)
    except Exception as e:
        return f"URL Error: {e}", None

    # Parse dates
    try:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except Exception as e:
        return f"Date format error (use YYYY-MM-DD): {e}", None

    start_str = start_date.strftime("%Y%m%d") + "00"
    end_str   = end_date.strftime("%Y%m%d") + "00"

    data1 = get_pageviews(article1, start_str, end_str)
    data2 = get_pageviews(article2, start_str, end_str)

    df1 = process_data(data1, article1)
    df2 = process_data(data2, article2)

    if df1.empty or df2.empty:
        return "No data returned from Wikipedia API", None

    merged_df = pd.merge(df1, df2, on="date", how="outer").sort_values("date")
    table_html = merged_df.head(20).to_html(index=False)

    # Quarterly Aggregation
    merged_df['date'] = pd.to_datetime(merged_df['date'])
    merged_df['quarter'] = merged_df['date'].dt.to_period('Q')
    quarter_df = merged_df.groupby('quarter').agg({
        f'views_{article1}': 'mean',
        f'views_{article2}': 'mean'
    }).reset_index()
    quarter_df['quarter_str'] = quarter_df['quarter'].apply(lambda r: f"Q{r.quarter} {r.year}")

    # Plotly Graph
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=quarter_df['quarter_str'], y=quarter_df[f'views_{article1}'],
                             mode='lines+markers', name=article1, marker=dict(color='red')))
    fig.add_trace(go.Scatter(x=quarter_df['quarter_str'], y=quarter_df[f'views_{article2}'],
                             mode='lines+markers', name=article2, marker=dict(color='blue')))
    fig.update_layout(
        title="Quarterly Average Daily Pageviews",
        xaxis_title="Quarter",
        yaxis_title="Avg Daily Views",
        plot_bgcolor="aliceblue",
        paper_bgcolor="lavender",
        hovermode="x unified"
    )

    return table_html, fig

# --- Gradio UI ---
demo = gr.Interface(
    fn=analyze_wiki,
    inputs=[
        gr.Textbox(label="Wikipedia URL 1"),
        gr.Textbox(label="Wikipedia URL 2"),
        gr.Textbox(label="Start Date (YYYY-MM-DD)"),
        gr.Textbox(label="End Date (YYYY-MM-DD)")
    ],
    outputs=[
        gr.HTML(label="Top 20 Daily Pageviews"),
        gr.Plot(label="Quarterly View Plot")
    ],
    title="📈 Wikipedia Pageview Analyzer",
    description="Enter two Wikipedia article URLs and a date range (YYYY-MM-DD) to compare their pageviews."
)

demo.launch()
