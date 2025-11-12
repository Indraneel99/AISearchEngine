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
/* Modern, clean UI with subtle glass and gradients */
:root {
  --radius-xl: 16px;
  --radius-lg: 14px;
  --radius-md: 12px;
  --shadow-lg: 0 18px 35px rgba(2, 6, 23, 0.10);
  --shadow-md: 0 10px 22px rgba(2, 6, 23, 0.08);
  --border: 1px solid rgba(2, 6, 23, 0.08);
  --primary: #6366f1; /* indigo-500 */
  --primary-600: #4f46e5;
  --primary-700: #4338ca;
  --slate-900: #0f172a;
  --slate-800: #1e293b;
  --slate-700: #334155;
  --slate-600: #475569;
  --slate-500: #64748b;
  --slate-200: #e2e8f0;
  --slate-100: #f1f5f9;
  --bg: radial-gradient(1200px 800px at 0% 0%, #f6f8ff 0%, #ffffff 40%);
}

.dark:root {
  --border: 1px solid rgba(255, 255, 255, 0.08);
  --bg: radial-gradient(1200px 800px at 0% 0%, #0b1220 0%, #0a0f1c 40%);
}

.gradio-container, body {
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Inter, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
  background: var(--bg);
  color: var(--slate-900);
}
.dark .gradio-container, .dark body { color: #e5e7eb; }

/* Header */
#app-header {
  background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 50%, #7c3aed 100%);
  color: white;
  padding: 28px 28px;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  margin-bottom: 18px;
}
#app-header h1 {
  font-size: 34px;
  line-height: 1.1;
  margin: 0 0 8px 0;
  letter-spacing: -0.02em;
}
#app-header p {
  margin: 0;
  opacity: 0.95;
}

/* Panels */
.panel {
  backdrop-filter: saturate(160%) blur(8px);
  background: rgba(255, 255, 255, 0.75);
  border: var(--border);
  border-radius: var(--radius-xl);
  padding: 18px;
  box-shadow: var(--shadow-md);
}
.dark .panel {
  background: rgba(2, 6, 23, 0.55);
}

/* Segmented control (radio) */
.segmented .wrap {
  display: grid !important;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  gap: 8px;
  background: var(--slate-100);
  border: var(--border);
  border-radius: 999px;
  padding: 6px;
}
.dark .segmented .wrap { background: rgba(255, 255, 255, 0.06); }
.segmented input[type="radio"] { display: none; }
.segmented label {
  border-radius: 999px !important;
  padding: 10px 14px !important;
  text-align: center;
  border: none !important;
  transition: all .18s ease;
  color: var(--slate-700);
  background: transparent;
}
.dark .segmented label { color: #cbd5e1; }
.segmented input[type="radio"]:checked + label {
  background: white !important;
  color: var(--slate-900) !important;
  box-shadow: 0 8px 18px rgba(2, 6, 23, 0.08);
}
.dark .segmented input[type="radio"]:checked + label {
  background: var(--slate-800) !important;
  color: #e5e7eb !important;
}

/* Form controls polish */
.panel .gr-form .gr-block, .panel .gr-form { gap: 10px; }
.panel .gr-textbox textarea, .panel .gr-textbox input,
.panel .gr-dropdown input, .panel .gr-dropdown .wrap,
.panel .gr-slider input {
  border-radius: 12px !important;
}

/* Submit button */
.submit-button .gr-button {
  background: linear-gradient(135deg, var(--primary), var(--primary-600));
  border: none;
  color: white;
  border-radius: 12px;
  box-shadow: 0 10px 24px rgba(79, 70, 229, 0.25);
  padding: 12px 16px;
}
.submit-button .gr-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 28px rgba(79, 70, 229, 0.32);
}

/* Output area */
.output-panel {
  padding: 0;
}
.model-info {
  margin-top: 8px;
}
.model-info .content {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  background: linear-gradient(135deg, #dcfce7, #dbeafe);
  color: #065f46;
  padding: 8px 12px;
  border-radius: 999px;
  border: var(--border);
}
.dark .model-info .content {
  background: linear-gradient(135deg, rgba(22, 101, 52, 0.35), rgba(30, 58, 138, 0.35));
  color: #d1fae5;
}

/* Results grid and cards */
.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
  padding: 14px;
}
.article-card {
  border: var(--border);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.9);
  padding: 16px;
  box-shadow: var(--shadow-md);
}
.dark .article-card {
  background: rgba(2, 6, 23, 0.6);
}
.article-card__title {
  font-size: 18px;
  margin: 0 0 8px 0;
  color: var(--slate-900);
}
.dark .article-card__title { color: #e5e7eb; }
.article-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
.chip {
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--slate-100);
  border: var(--border);
  color: var(--slate-700);
}
.dark .chip { background: rgba(255, 255, 255, 0.06); color: #cbd5e1; }
.article-card__authors {
  color: var(--slate-600);
  font-size: 14px;
  margin-bottom: 10px;
}
.dark .article-card__authors { color: #94a3b8; }
.article-card__link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--primary-600);
  text-decoration: none;
  font-weight: 600;
}
.article-card__link:hover { color: var(--primary-700); }

/* AI answer card */
.answer-card {
  margin: 14px;
  border: var(--border);
  border-radius: var(--radius-xl);
  padding: 18px;
  background: linear-gradient(180deg, rgba(99, 102, 241, 0.06), rgba(124, 58, 237, 0.06));
  box-shadow: var(--shadow-md);
}
.dark .answer-card {
  background: linear-gradient(180deg, rgba(79, 70, 229, 0.18), rgba(124, 58, 237, 0.18));
}
.answer-card .markdown-body table {
  width: 100%;
  border-collapse: collapse;
}
.answer-card .markdown-body th, .answer-card .markdown-body td {
  border: 1px solid rgba(0,0,0,0.05);
  padding: 6px 10px;
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

        html_output = "<div class='results-grid'>"
        for item in results:
            title = item.get("title", "No title")
            feed_n = item.get("feed_name", "N/A")
            feed_a = item.get("feed_author", "N/A")
            authors = ", ".join(item.get("article_author") or ["N/A"])
            url = item.get("url", "#")
            html_output += (
                "<div class='article-card'>"
                f"  <h3 class='article-card__title'>{title}</h3>"
                f"  <div class='article-card__meta'>"
                f"    <span class='chip'>Newsletter: {feed_n}</span>"
                f"    <span class='chip'>Author: {feed_a}</span>"
                f"  </div>"
                f"  <div class='article-card__authors'><b>Article Authors:</b> {authors}</div>"
                f"  <a class='article-card__link' href='{url}' target='_blank' rel='noopener noreferrer'>"
                f"     Open Article →"
                f"  </a>"
                "</div>"
            )
        html_output += "</div>"
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
        model_info = f"<div class='content'>Provider: {provider}</div>"

        for _, (event_type, content) in enumerate(call_ai(payload, streaming=True)):
            if event_type == "text":
                # Convert markdown to HTML
                html_content = markdown.markdown(content, extensions=["tables"])
                answer_html = f"<div class='answer-card'><div class='markdown-body'>{html_content}</div></div>"
                yield answer_html, model_info

            elif event_type == "model":
                model_info = f"<div class='content'>Provider: {provider} | Model: {content}</div>"
                yield answer_html, model_info

            elif event_type == "truncated":
                answer_html += f"<div class='answer-card'><div style='color:#ff8800; font-weight:700;'>⚠️ {content}</div></div>"
                yield answer_html, model_info

            elif event_type == "error":
                error_html = f"<div class='answer-card'><div style='color:#ef4444; font-weight:700;'>❌ {content}</div></div>"
                yield error_html, model_info
                break

    except Exception as e:
        error_html = "<div class='answer-card'><div style='color:#ef4444;'>Error: {}</div></div>".format(str(e))
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
        model_info = f"<div class='content'>Provider: {provider}</div>"

        for event_type, content in call_ai(payload, streaming=False):
            if event_type == "text":
                html_content = markdown.markdown(content, extensions=["tables"])
                answer_html = f"<div class='answer-card'><div class='markdown-body'>{html_content}</div></div>"
            elif event_type == "model":
                model_info = f"<div class='content'>Provider: {provider} | Model: {content}</div>"
            elif event_type == "truncated":
                answer_html += f"<div class='answer-card'><div style='color:#ff8800; font-weight:700;'>⚠️ {content}</div></div>"
            elif event_type == "error":
                return (
                    f"<div class='answer-card'><div style='color:#ef4444; font-weight:700;'>❌ {content}</div></div>",
                    model_info,
                )

        return answer_html, model_info

    except Exception as e:
        return (
            f"<div class='answer-card'><div style='color:#ef4444;'>Error: {str(e)}</div></div>",
            f"<div class='content'>Provider: {provider}</div>",
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
# Gradio UI
# -----------------------
with gr.Blocks(title="AI Search Engine for Articles", theme=gr.themes.Soft(), css=CUSTOM_CSS) as demo:
    # Header
    gr.HTML(
        "<div id='app-header'>"
        "  <h1>📰 AI Search Engine for Articles</h1>"
        "  <p>Search Substack, Medium and top publications content or ask an AI across your feeds — fast and delightful.</p>"
        "</div>"
    )

    with gr.Row():
        with gr.Column(scale=5):
            with gr.Group(elem_classes="panel"):
                gr.Markdown("#### Mode")
                search_type = gr.Radio(
                    choices=["Search Articles", "Ask the AI"],
                    value="Search Articles",
                    label="",
                    info="Choose between searching for articles or asking AI questions",
                    elem_classes="segmented",
                )

                with gr.Accordion("Filters", open=True):
                    query_text = gr.Textbox(
                        label="Query",
                        placeholder="Type your query here...",
                        lines=4,
                    )
                    feed_author = gr.Dropdown(
                        choices=[""] + feed_authors, label="Author (optional)", value=""
                    )
                    feed_name = gr.Dropdown(
                        choices=[""] + feed_names, label="Newsletter (optional)", value=""
                    )
                    title_keywords = gr.Textbox(
                        label="Title Keywords (optional)",
                        placeholder="Filter by words in the title",
                        visible=True,
                    )
                    limit = gr.Slider(
                        minimum=1, maximum=20, step=1, label="Number of results", value=5, visible=True
                    )

                with gr.Accordion("⚙️ LLM Settings", open=True):
                    with gr.Group(visible=False) as llm_options:
                        provider = gr.Dropdown(
                            choices=["OpenRouter", "HuggingFace", "OpenAI"],
                            label="Select LLM Provider",
                            value="OpenRouter",
                        )
                        model = gr.Dropdown(
                            choices=get_models_for_provider("OpenRouter"),
                            label="Select Model",
                            value="Automatic Model Selection (Model Routing)",
                        )
                        streaming_mode = gr.Radio(
                            choices=["Streaming", "Non-Streaming"],
                            value="Streaming",
                            label="Answer Mode",
                            info="Streaming shows results as they're generated",
                        )

                submit_btn = gr.Button("🔎 Search / Ask AI", variant="primary", size="lg", elem_classes="submit-button")

        with gr.Column(scale=7):
            with gr.Group(elem_classes="panel output-panel"):
                output_html = gr.HTML(label="Results")
                model_info = gr.HTML(visible=False, elem_classes="model-info")

    # Event handlers
    def toggle_visibility(search_type):
        """
        Toggle visibility of components based on search type

        Args:
            search_type (str): The selected search type
        Returns:
            tuple: Visibility states for (llm_options, title_keywords, model_info)
        """

        show_title_keywords = search_type == "Search Articles"
        show_llm_options = search_type == "Ask the AI"
        show_model_info = search_type == "Ask the AI"
        show_limit_slider = search_type == "Search Articles"

        return (
            gr.Group(visible=show_llm_options),  # llm_options
            gr.Textbox(visible=show_title_keywords),  # title_keywords
            gr.HTML(visible=show_model_info),  # model_info
            gr.Slider(visible=show_limit_slider),  # limit
        )

    search_type.change(
        fn=toggle_visibility,
        inputs=[search_type],
        outputs=[llm_options, title_keywords, model_info, limit],
    )

    # Update model dropdown when provider changes
    provider.change(fn=update_model_choices, inputs=[provider], outputs=[model])

    # Unified submission handler
    def handle_submission(
        search_type,
        streaming_mode,
        query_text,
        feed_name,
        feed_author,
        title_keywords,
        limit,
        provider,
        model,
    ):
        """
        Handle submission based on search type and streaming mode
        Args:
            search_type (str): The selected search type
            streaming_mode (str): The selected streaming mode
            query_text (str): The query text
            feed_name (str): The selected feed name
            feed_author (str): The selected feed author
            title_keywords (str): The title keywords (if applicable)
            limit (int): The number of results to return
            provider (str): The selected LLM provider (if applicable)
            model (str): The selected model (if applicable)
        Returns:
            tuple: (HTML formatted answer string, model info string)
        """
        if search_type == "Search Articles":
            result = handle_search_articles(
                query_text, feed_name, feed_author, title_keywords, limit
            )
            return result, ""  # Always return two values
        else:  # Ask the AI
            if streaming_mode == "Non-Streaming":
                return handle_ai_question_non_streaming(
                    query_text, feed_name, feed_author, limit, provider, model
                )
            else:
                # For streaming, we'll use a separate handler
                return "", ""

    # Streaming handler
    def handle_streaming_submission(
        search_type,
        streaming_mode,
        query_text,
        feed_name,
        feed_author,
        title_keywords,
        limit,
        provider,
        model,
    ):
        """
        Handle submission with streaming support
        Args:
            search_type (str): The selected search type
            streaming_mode (str): The selected streaming mode
            query_text (str): The query text
            feed_name (str): The selected feed name
            feed_author (str): The selected feed author
            title_keywords (str): The title keywords (if applicable)
            limit (int): The number of results to return
            provider (str): The selected LLM provider (if applicable)
            model (str): The selected model (if applicable)
        Yields:
            tuple: (HTML formatted answer string, model info string)
        """
        if search_type == "Ask the AI" and streaming_mode == "Streaming":
            yield from handle_ai_question_streaming(
                query_text, feed_name, feed_author, limit, provider, model
            )
        else:
            # For non-streaming cases, just return the regular result
            if search_type == "Search Articles":
                result = handle_search_articles(
                    query_text, feed_name, feed_author, title_keywords, limit
                )
                yield result, ""
            else:
                result_html, model_info_text = handle_ai_question_non_streaming(
                    query_text, feed_name, feed_author, limit, provider, model
                )
                yield result_html, model_info_text

    # Single click handler that routes based on mode
    submit_btn.click(
        fn=handle_streaming_submission,
        inputs=[
            search_type,
            streaming_mode,
            query_text,
            feed_name,
            feed_author,
            title_keywords,
            limit,
            provider,
            model,
        ],
        outputs=[output_html, model_info],
        show_progress=True,
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
