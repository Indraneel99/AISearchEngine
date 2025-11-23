import os

import gradio as gr
import markdown
import requests
import yaml
from dotenv import load_dotenv

try:
    from src.api.models.provider_models import MODEL_REGISTRY
except ImportError as e:
    raise ImportError(
        "Could not import MODEL_REGISTRY from src.api.models.provider_models. "
        "Check the path and file existence."
    ) from e

# Initialize environment variables
load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
API_BASE_URL = f"{BACKEND_URL}/search"


# Load feeds from YAML
def load_feeds():
    """Load feeds from the YAML configuration file.
    Returns:
        list: List of feeds with their details.
    """
    feeds_path = os.path.join(os.path.dirname(__file__), "../src/configs/feeds_rss.yaml")
    with open(feeds_path) as f:
        feeds_yaml = yaml.safe_load(f)
    return feeds_yaml.get("feeds", [])


feeds = load_feeds()
feed_names = [f["name"] for f in feeds]
feed_authors = [f["author"] for f in feeds]


# -----------------------
# Custom CSS for modern UI
# -----------------------
CUSTOM_CSS = """
/* Minimal, utility-first vibe with a neutral palette */
:root {
  --border: 1px solid rgba(2, 6, 23, 0.08);
  --surface: #ffffff;
  --surface-muted: #f8fafc;
  --text: #0f172a;
  --muted: #475569;
  --accent: #0ea5e9;
  --accent-strong: #0284c7;
  --radius: 12px;
  --shadow: 0 8px 20px rgba(2, 6, 23, 0.06);
}

.gradio-container, body {
  background: var(--surface-muted);
  color: var(--text);
}

.dark .gradio-container, .dark body {
  background: #0b1220;
  color: #e5e7eb;
}

.section {
  background: var(--surface);
  border: var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px;
}

.dark .section {
  background: #0f172a;
  border: 1px solid rgba(255,255,255,0.08);
}

.header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
}
.header h2 {
  margin: 0;
  font-size: 22px;
}
.subtle {
  color: var(--muted);
  font-size: 13px;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.results-table th, .results-table td {
  border: 1px solid #e2e8f0;
  padding: 10px;
  text-align: left;
  vertical-align: top;
}
.results-table th {
  background: #f1f5f9;
}
.dark .results-table th {
  background: #0b1325;
  border-color: rgba(255,255,255,0.08);
  color: #e5e7eb;
}
.dark .results-table td {
  border-color: rgba(255,255,255,0.08);
  color: #e2e8f0;
}
.results-table a {
  color: var(--accent-strong);
  text-decoration: none;
  font-weight: 600;
}
.results-table a:hover {
  text-decoration: underline;
}
.dark .results-table a {
  color: #7dd3fc;
}

.answer {
  background: var(--surface);
  border: var(--border);
  border-radius: var(--radius);
  padding: 14px;
}
.dark .answer {
  background: #0f172a;
  border: 1px solid rgba(255,255,255,0.08);
  color: #e5e7eb;
}
.model-badge {
  display: inline-block;
  margin-top: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  border: var(--border);
  background: #eef2ff;
  color: #3730a3;
  font-weight: 600;
}
.dark .model-badge {
  background: rgba(59,130,246,0.15);
  color: #c7d2fe;
  border: 1px solid rgba(255,255,255,0.08);
}
.error {
  border: 1px solid #fecaca;
  background: #fff1f2;
  color: #7f1d1d;
  border-radius: var(--radius);
  padding: 10px 12px;
}
.dark .error {
  border: 1px solid rgba(248,113,113,0.35);
  background: rgba(127,29,29,0.25);
  color: #fecaca;
}

/* Sticky status banner with spinner */
#status-banner {
  position: sticky;
  top: 0;
  z-index: 1000;
  margin: 8px 0 12px 0;
}
#status-banner .banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius);
  border: 1px solid #bae6fd;
  background: #e0f2fe;
  color: #075985;
  box-shadow: var(--shadow);
}
#status-banner .spinner {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.dark #status-banner .banner {
  border-color: rgba(59,130,246,0.35);
  background: rgba(2,6,23,0.55);
  color: #93c5fd;
}

/* Actions row aligns buttons to the right, outside filter sections */
.actions {
  display: flex;
  justify-content: flex-end;
  margin: 8px 0 12px 0;
  gap: 8px;
}

/* Prominent CTA buttons (not full-width) */
.cta {
  display: inline-flex;
}
.cta .gr-button {
  background: linear-gradient(180deg, var(--accent), var(--accent-strong));
  color: #ffffff;
  border: none;
  border-radius: 14px;
  padding: 12px 18px;
  font-weight: 700;
  font-size: 15px;
  box-shadow: 0 10px 22px rgba(2,6,23,0.18);
  width: auto !important;
}
.cta .gr-button:hover {
  transform: translateY(-1px);
  filter: brightness(1.05);
}
.cta .gr-button:focus-visible {
  outline: 2px solid #93c5fd;
  outline-offset: 2px;
}
.dark .cta .gr-button {
  box-shadow: 0 12px 26px rgba(2,6,23,0.45);
}
"""


# -----------------------
# API helpers
# -----------------------
def fetch_unique_titles(payload):
    """
    Fetch unique article titles based on the search criteria.

    Args:
        payload (dict): The search criteria including query_text, feed_author,
                        feed_name, limit, and optional title_keywords.
    Returns:
        list: A list of articles matching the criteria.
    Raises:
        Exception: If the API request fails.
    """
    try:
        resp = requests.post(f"{API_BASE_URL}/unique-titles", json=payload)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except Exception as e:
        raise Exception(f"Failed to fetch titles: {str(e)}") from e


def call_ai(payload, streaming=True):
    """ "
    Call the AI endpoint with the given payload.
    Args:
        payload (dict): The payload to send to the AI endpoint.
        streaming (bool): Whether to use streaming or non-streaming endpoint.
    Yields:
        tuple: A tuple containing the type of response and the response text.
    """
    endpoint = f"{API_BASE_URL}/ask/stream" if streaming else f"{API_BASE_URL}/ask"
    answer_text = ""
    try:
        if streaming:
            with requests.post(endpoint, json=payload, stream=True) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                    if not chunk:
                        continue
                    if chunk.startswith("__model_used__:"):
                        yield "model", chunk.replace("__model_used__:", "").strip()
                    elif chunk.startswith("__error__"):
                        yield "error", "Request failed. Please try again later."
                        break
                    elif chunk.startswith("__truncated__"):
                        yield "truncated", "AI response truncated due to token limit."
                    else:
                        answer_text += chunk
                        yield "text", answer_text
        else:
            resp = requests.post(endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()
            answer_text = data.get("answer", "")
            yield "text", answer_text
            if data.get("finish_reason") == "length":
                yield "truncated", "AI response truncated due to token limit."
    except Exception as e:
        yield "error", f"Request failed: {str(e)}"


def get_models_for_provider(provider):
    """
    Get available models for a provider

    Args:
        provider (str): The name of the provider (e.g., "openrouter", "openai")
    Returns:
        list: List of model names available for the provider
    """
    provider_key = provider.lower()
    try:
        config = MODEL_REGISTRY.get_config(provider_key)
        return (
            ["Automatic Model Selection (Model Routing)"]
            + ([config.primary_model] if config.primary_model else [])
            + list(config.candidate_models)
        )
    except Exception:
        return ["Automatic Model Selection (Model Routing)"]


# -----------------------
# Gradio interface functions
# -----------------------
def handle_search_articles(query_text, feed_name, feed_author, title_keywords, limit):
    """
    Handle article search

    Args:
        query_text (str): The text to search for in article titles.
        feed_name (str): The name of the feed to filter articles by.
        feed_author (str): The author of the feed to filter articles by.
        title_keywords (str): Keywords to search for in article titles.
        limit (int): The maximum number of articles to return.
    Returns:
        str: HTML formatted string of search results or error message.
    Raises:
        Exception: If the API request fails.
    """
    if not query_text.strip():
        return "Please enter a query text."

    payload = {
        "query_text": query_text.strip().lower(),
        "feed_author": feed_author.strip() if feed_author else "",
        "feed_name": feed_name.strip() if feed_name else "",
        "limit": limit,
        "title_keywords": title_keywords.strip().lower() if title_keywords else None,
    }

    try:
        results = fetch_unique_titles(payload)
        if not results:
            return "No results found."

        # Render results as a compact table
        html_output = (
            "<div class='section'>"
            "  <div class='header'><h2>Results</h2><span class='subtle'>Unique titles</span></div>"
            "  <table class='results-table'>"
            "    <thead>"
            "      <tr><th>Title</th><th>Newsletter</th><th>Feed Author</th><th>Article Authors</th><th>Link</th></tr>"
            "    </thead>"
            "    <tbody>"
        )
        for item in results:
            title = item.get("title", "No title")
            feed_n = item.get("feed_name", "N/A")
            feed_a = item.get("feed_author", "N/A")
            authors = ", ".join(item.get("article_author") or ["N/A"])
            url = item.get("url", "#")
            html_output += (
                "      <tr>"
                f"        <td>{title}</td>"
                f"        <td>{feed_n}</td>"
                f"        <td>{feed_a}</td>"
                f"        <td>{authors}</td>"
                f"        <td><a href='{url}' target='_blank' rel='noopener noreferrer'>Open</a></td>"
                "      </tr>"
            )
        html_output += "    </tbody></table></div>"
        return html_output

    except Exception as e:
        return f"<div style='color:red; padding:10px;'>Error: {str(e)}</div>"


def handle_ai_question_streaming(
    query_text,
    feed_name,
    feed_author,
    limit,
    provider,
    model,
):
    """
    Handle AI question with streaming

    Args:
        query_text (str): The question to ask the AI.
        feed_name (str): The name of the feed to filter articles by.
        feed_author (str): The author of the feed to filter articles by.
        limit (int): The maximum number of articles to consider.
        provider (str): The LLM provider to use.
        model (str): The specific model to use from the provider.
    Yields:
        tuple: (HTML formatted answer string, model info string)
    """
    if not query_text.strip():
        yield "Please enter a query text.", ""
        return

    if not provider or not model:
        yield "Please select provider and model.", ""
        return

    payload = {
        "query_text": query_text.strip().lower(),
        "feed_author": feed_author.strip() if feed_author else "",
        "feed_name": feed_name.strip() if feed_name else "",
        "limit": limit,
        "provider": provider.lower(),
    }

    if model != "Automatic Model Selection (Model Routing)":
        payload["model"] = model

    try:
        answer_html = ""
        model_info = f"<span class='model-badge'>Provider: {provider}</span>"

        for _, (event_type, content) in enumerate(call_ai(payload, streaming=True)):
            if event_type == "text":
                html_content = markdown.markdown(content, extensions=["tables"])
                answer_html = f"<div class='answer'><div class='markdown-body'>{html_content}</div></div>"
                yield answer_html, model_info

            elif event_type == "model":
                model_info = f"<span class='model-badge'>Provider: {provider} | Model: {content}</span>"
                yield answer_html, model_info

            elif event_type == "truncated":
                answer_html += f"<div class='answer'><div style='color:#b45309; font-weight:700;'>⚠️ {content}</div></div>"
                yield answer_html, model_info

            elif event_type == "error":
                error_html = f"<div class='error'><div>❌ {content}</div></div>"
                yield error_html, model_info
                break

    except Exception as e:
        error_html = "<div class='error'>Error: {}</div>".format(str(e))
        yield error_html, model_info


def handle_ai_question_non_streaming(query_text, feed_name, feed_author, limit, provider, model):
    """
    Handle AI question without streaming

    Args:
        query_text (str): The question to ask the AI.
        feed_name (str): The name of the feed to filter articles by.
        feed_author (str): The author of the feed to filter articles by.
        limit (int): The maximum number of articles to consider.
        provider (str): The LLM provider to use.
        model (str): The specific model to use from the provider.

    Returns:
        tuple: (HTML formatted answer string, model info string)
    """
    if not query_text.strip():
        return "Please enter a query text.", ""

    if not provider or not model:
        return "Please select provider and model.", ""

    payload = {
        "query_text": query_text.strip().lower(),
        "feed_author": feed_author.strip() if feed_author else "",
        "feed_name": feed_name.strip() if feed_name else "",
        "limit": limit,
        "provider": provider.lower(),
    }

    if model != "Automatic Model Selection (Model Routing)":
        payload["model"] = model

    try:
        answer_html = ""
        model_info = f"<span class='model-badge'>Provider: {provider}</span>"

        for event_type, content in call_ai(payload, streaming=False):
            if event_type == "text":
                html_content = markdown.markdown(content, extensions=["tables"])
                answer_html = f"<div class='answer'><div class='markdown-body'>{html_content}</div></div>"
            elif event_type == "model":
                model_info = f"<span class='model-badge'>Provider: {provider} | Model: {content}</span>"
            elif event_type == "truncated":
                answer_html += f"<div class='answer'><div style='color:#b45309; font-weight:700;'>⚠️ {content}</div></div>"
            elif event_type == "error":
                return (
                    f"<div class='error'>❌ {content}</div>",
                    model_info,
                )

        return answer_html, model_info

    except Exception as e:
        return (
            f"<div class='error'>Error: {str(e)}</div>",
            f"<span class='model-badge'>Provider: {provider}</span>",
        )


def update_model_choices(provider):
    """
    Update model choices based on selected provider
    Args:
        provider (str): The selected LLM provider
    Returns:
        gr.Dropdown: Updated model dropdown component
    """
    models = get_models_for_provider(provider)
    return gr.Dropdown(choices=models, value=models[0] if models else "")


# -----------------------
# Progress/status helpers
# -----------------------
def start_search_status():
    return "<div class='banner'><span class='spinner'></span><strong>Searching articles...</strong></div>"


def start_ai_status(streaming_mode):
    mode = "streaming" if streaming_mode == "Streaming" else "non‑streaming"
    return f"<div class='banner'><span class='spinner'></span><strong>Generating answer ({mode})...</strong></div>"


def clear_status():
    return ""


# -----------------------
# Gradio UI (new layout)
# -----------------------
def ask_ai_router(
    streaming_mode,
    query_text,
    feed_name,
    feed_author,
    limit,
    provider,
    model,
):
    """
    Route AI question to streaming or non-streaming handler.
    Yields:
        tuple: (answer_html, model_info_html)
    """
    if streaming_mode == "Streaming":
        yield from handle_ai_question_streaming(
            query_text, feed_name, feed_author, limit, provider, model
        )
    else:
        result_html, model_info_text = handle_ai_question_non_streaming(
            query_text, feed_name, feed_author, limit, provider, model
        )
        yield result_html, model_info_text


with gr.Blocks(title="Article Search Engine", theme=gr.themes.Base(), css=CUSTOM_CSS) as demo:
    gr.Markdown(
        "### Article Search Engine\n"
        "Search across substack, medium and top publications articles on AI topics or ask questions with an AI assistant."
    )

    # Sticky status banner (empty by default)
    status_banner = gr.HTML(value="", elem_id="status-banner")

    with gr.Tabs():
        # Search Tab
        with gr.Tab("Search"):
            with gr.Group(elem_classes="section"):
                gr.Markdown("#### Find articles on any AI topic")
                search_query = gr.Textbox(
                    label="Query",
                    placeholder="What are you looking for?",
                    lines=3,
                )
                with gr.Row():
                    search_feed_author = gr.Dropdown(
                        choices=[""] + feed_authors, label="Author (optional)", value=""
                    )
                    search_feed_name = gr.Dropdown(
                        choices=[""] + feed_names, label="Newsletter (optional)", value=""
                    )
                with gr.Row():
                    search_title_keywords = gr.Textbox(
                        label="Title keywords (optional)",
                        placeholder="Filter by words in the title",
                    )
                    search_limit = gr.Slider(
                        minimum=1, maximum=20, step=1, label="Number of results", value=5
                    )
            with gr.Row(elem_classes="actions"):
                search_btn = gr.Button("Search", variant="primary", elem_classes="cta")
            search_output = gr.HTML(label="Results")

        # Ask AI Tab
        with gr.Tab("Ask AI"):
            with gr.Group(elem_classes="section"):
                gr.Markdown("#### Ask an AI assistant about any AI topic")
                ai_query = gr.Textbox(
                    label="Your question",
                    placeholder="Ask a question. The AI will use the articles for context.",
                    lines=4,
                )
                with gr.Row():
                    ai_feed_author = gr.Dropdown(
                        choices=[""] + feed_authors, label="Author (optional)", value=""
                    )
                    ai_feed_name = gr.Dropdown(
                        choices=[""] + feed_names, label="Newsletter (optional)", value=""
                    )
                    ai_limit = gr.Slider(
                        minimum=1, maximum=20, step=1, label="Max articles", value=5
                    )
                with gr.Row():
                    provider_dd = gr.Dropdown(
                        choices=["OpenRouter", "HuggingFace", "OpenAI"],
                        label="LLM Provider",
                        value="OpenRouter",
                    )
                    model_dd = gr.Dropdown(
                        choices=get_models_for_provider("OpenRouter"),
                        label="Model",
                        value="Automatic Model Selection (Model Routing)",
                    )
                    streaming_mode_dd = gr.Radio(
                        choices=["Streaming", "Non-Streaming"],
                        value="Streaming",
                        label="Answer mode",
                    )
            with gr.Row(elem_classes="actions"):
                ask_btn = gr.Button("Run", variant="primary", elem_classes="cta")
            ai_answer = gr.HTML(label="Answer")
            ai_model_info = gr.HTML(label="Model")

    # Wire events with sticky status banner
    search_btn.click(
        fn=start_search_status,
        inputs=[],
        outputs=[status_banner],
        show_progress=False,
    ).then(
        fn=handle_search_articles,
        inputs=[
            search_query,
            search_feed_name,
            search_feed_author,
            search_title_keywords,
            search_limit,
        ],
        outputs=[search_output],
        show_progress=False,
    ).then(
        fn=clear_status,
        inputs=[],
        outputs=[status_banner],
        show_progress=False,
    )

    provider_dd.change(fn=update_model_choices, inputs=[provider_dd], outputs=[model_dd])

    ask_btn.click(
        fn=start_ai_status,
        inputs=[streaming_mode_dd],
        outputs=[status_banner],
        show_progress=False,
    ).then(
        fn=ask_ai_router,
        inputs=[
            streaming_mode_dd,
            ai_query,
            ai_feed_name,
            ai_feed_author,
            ai_limit,
            provider_dd,
            model_dd,
        ],
        outputs=[ai_answer, ai_model_info],
        show_progress=False,
    ).then(
        fn=clear_status,
        inputs=[],
        outputs=[status_banner],
        show_progress=False,
    )

# For local testing
if __name__ == "__main__":
    demo.launch()

# # For Google Cloud Run deployment
# if __name__ == "__main__":
#     demo.launch(
#         server_name="0.0.0.0",
#         server_port=int(os.environ.get("PORT", 8080))
#     )
