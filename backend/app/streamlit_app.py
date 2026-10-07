import json
import os
import sys
import textwrap
import tempfile
from collections import Counter

import streamlit as st
import yt_dlp


# =========================================================
# PROJECT / MODEL PATH
# =========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

MODEL_DIR = os.path.join(
    PROJECT_ROOT,
    "model",
)

sys.path.insert(
    0,
    MODEL_DIR,
)

from scripts.spot_video import run_inference


# =========================================================
# YOUTUBE DOWNLOAD
# =========================================================

def download_youtube_video(url, output_dir):
    """
    Download a YouTube video into the supplied temporary directory.

    Returns:
        str: Path to the downloaded video.
    """

    output_template = os.path.join(
        output_dir,
        "youtube_match.%(ext)s",
    )

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=True,
            )

            downloaded_path = ydl.prepare_filename(info)

            # yt-dlp  merges the video into MP4
            possible_mp4 = os.path.splitext(
                downloaded_path
            )[0] + ".mp4"

            if os.path.exists(possible_mp4):
                return possible_mp4

            if os.path.exists(downloaded_path):
                return downloaded_path

            raise FileNotFoundError(
                "Downloaded video could not be located."
            )

    except Exception as e:

        raise RuntimeError(
            f"Unable to download the YouTube video: {e}"
        ) from e



# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="PitchVision | Football Intelligence",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================================================
# PITCHVISION DESIGN SYSTEM — V2
# =========================================================

st.markdown(
    """
    <style>
    :root {
        --pv-bg: #071018;
        --pv-surface: #0d1721;
        --pv-surface-2: #111e2a;
        --pv-border: #1d2b38;
        --pv-text: #f5f7fa;
        --pv-muted: #8ea0b3;
        --pv-muted-2: #607285;
        --pv-accent: #10b981;
        --pv-accent-dark: #087f5b;
        --pv-warning: #f59e0b;
    }

    .stApp {
        background:
            radial-gradient(circle at 85% 0%, rgba(16,185,129,.08), transparent 27%),
            radial-gradient(circle at 0% 25%, rgba(14,165,233,.035), transparent 24%),
            var(--pv-bg);
        color: var(--pv-text);
    }

    .block-container {
        max-width: 1480px;
        padding-top: 1.4rem;
        padding-bottom: 3rem;
    }

    #MainMenu, footer { visibility: hidden; }
    header { background: transparent !important; }

    /* ---------- Brand ---------- */

    .pv-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.1rem;
    }

    .pv-brand-wrap {
        display: flex;
        align-items: center;
        gap: .8rem;
    }

    .pv-logo {
        width: 44px;
        height: 44px;
        border-radius: 13px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--pv-accent);
        color: #04110c;
        font-size: 1.35rem;
        box-shadow: 0 8px 28px rgba(16,185,129,.18);
    }

    .pv-brand {
        color: #fff;
        font-size: 1.45rem;
        font-weight: 850;
        letter-spacing: -.04em;
        line-height: 1;
    }

    .pv-tagline {
        color: var(--pv-muted);
        font-size: .75rem;
        margin-top: .22rem;
    }

    .pv-status {
        color: #8cebc9;
        background: rgba(16,185,129,.08);
        border: 1px solid rgba(16,185,129,.2);
        border-radius: 999px;
        padding: .35rem .7rem;
        font-size: .72rem;
        font-weight: 750;
    }

    /* ---------- Hero / intro ---------- */

    .pv-hero {
        border: 1px solid var(--pv-border);
        border-radius: 20px;
        padding: 1.55rem 1.65rem;
        margin-bottom: 1.1rem;
        background:
            linear-gradient(135deg, rgba(16,185,129,.12), rgba(13,23,33,.86) 55%),
            var(--pv-surface);
    }

    .pv-eyebrow {
        color: #56d9ad;
        font-size: .68rem;
        text-transform: uppercase;
        letter-spacing: .15em;
        font-weight: 850;
        margin-bottom: .35rem;
    }

    .pv-title {
        color: #fff;
        font-size: clamp(1.65rem, 3vw, 2.35rem);
        font-weight: 850;
        letter-spacing: -.045em;
        line-height: 1.05;
    }

    .pv-description {
        color: var(--pv-muted);
        max-width: 760px;
        line-height: 1.55;
        margin-top: .55rem;
        font-size: .92rem;
    }

    /* ---------- Section headings ---------- */

    .pv-section {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 1rem;
        margin: 1.45rem 0 .7rem;
    }

    .pv-section-title {
        color: #f8fafc;
        font-size: 1.02rem;
        font-weight: 820;
        letter-spacing: -.015em;
    }

    .pv-section-subtitle {
        color: var(--pv-muted-2);
        font-size: .74rem;
    }

    /* ---------- Cards ---------- */

    .pv-card {
        background: var(--pv-surface);
        border: 1px solid var(--pv-border);
        border-radius: 16px;
        padding: 1rem;
    }

    .pv-card-tight {
        min-height: 100%;
    }

    .metric-card {
        background: var(--pv-surface);
        border: 1px solid var(--pv-border);
        border-radius: 15px;
        padding: 1rem 1.05rem;
        min-height: 106px;
    }

    .metric-label {
        color: var(--pv-muted);
        font-size: .67rem;
        text-transform: uppercase;
        letter-spacing: .09em;
        font-weight: 800;
    }

    .metric-value {
        color: #fff;
        font-size: 1.8rem;
        line-height: 1.1;
        font-weight: 880;
        margin-top: .35rem;
    }

    .metric-description {
        color: var(--pv-muted-2);
        font-size: .73rem;
        margin-top: .25rem;
    }

    /* ---------- Upload ---------- */

    .upload-card {
        border: 1px dashed #365064;
        border-radius: 18px;
        padding: 2rem 1.4rem;
        text-align: center;
        background: rgba(13,23,33,.72);
        margin-bottom: .5rem;
    }

    .upload-icon {
        font-size: 2rem;
        margin-bottom: .35rem;
    }

    .upload-title {
        color: #fff;
        font-size: 1.08rem;
        font-weight: 800;
    }

    .upload-copy {
        color: var(--pv-muted);
        font-size: .82rem;
        margin-top: .25rem;
    }

    /* ---------- Key moments ---------- */

    .moment-card {
        background: linear-gradient(135deg, #101d28, #0c151e);
        border: 1px solid var(--pv-border);
        border-radius: 15px;
        padding: .95rem 1rem;
        min-height: 125px;
    }

    .moment-time {
        color: #56d9ad;
        font-size: .72rem;
        font-weight: 850;
        letter-spacing: .06em;
    }

    .moment-title {
        color: #fff;
        font-weight: 800;
        margin-top: .3rem;
    }

    .moment-meta {
        color: var(--pv-muted);
        font-size: .75rem;
        margin-top: .25rem;
    }

    /* ---------- Breakdown ---------- */

    .breakdown-row {
        display: grid;
        grid-template-columns: 90px 1fr 42px;
        align-items: center;
        gap: .7rem;
        margin: .7rem 0;
    }

    .breakdown-label {
        color: #dce4eb;
        font-size: .78rem;
        font-weight: 750;
    }

    .breakdown-track {
        height: 7px;
        background: #172531;
        border-radius: 99px;
        overflow: hidden;
    }

    .breakdown-fill {
        height: 100%;
        background: var(--pv-accent);
        border-radius: 99px;
    }

    .breakdown-count {
        color: var(--pv-muted);
        font-size: .75rem;
        text-align: right;
        font-weight: 750;
    }

    /* ---------- Event cards ---------- */

    .event-card {
        background: var(--pv-surface);
        border: 1px solid var(--pv-border);
        border-radius: 14px;
        padding: .8rem .9rem;
        margin-bottom: .55rem;
    }

    .event-time {
        color: #56d9ad;
        font-weight: 850;
        font-size: .78rem;
    }

    .event-name {
        color: #fff;
        font-weight: 800;
        font-size: .86rem;
    }

    .event-confidence {
        color: var(--pv-muted);
        font-size: .72rem;
    }

    .confidence-track {
        height: 4px;
        background: #172531;
        border-radius: 99px;
        overflow: hidden;
        margin-top: .45rem;
    }

    .confidence-fill {
        height: 100%;
        background: var(--pv-accent);
        border-radius: 99px;
    }

    /* ---------- Empty / info ---------- */

    .empty-state {
        border: 1px dashed #2b4151;
        border-radius: 14px;
        padding: 1.2rem;
        color: var(--pv-muted);
        text-align: center;
        background: rgba(13,23,33,.55);
    }

    .pv-footer {
        color: #526477;
        text-align: center;
        font-size: .7rem;
        padding: 1.5rem 0 .2rem;
    }

    /* ---------- Streamlit controls ---------- */

    .stButton > button {
        border-radius: 10px !important;
        font-weight: 760 !important;
        min-height: 2.55rem;
    }

    .stTextInput input,
    .stSelectbox div[data-baseweb="select"] > div,
    .stNumberInput input {
        border-radius: 10px !important;
    }

    [data-testid="stFileUploader"] {
        border-radius: 14px;
    }

    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
    }

    [data-testid="stSidebar"] {
        background: #060c12;
        border-right: 1px solid var(--pv-border);
    }

    /* Keep native video rounded */
    video {
        border-radius: 14px;
    }

    @media (max-width: 800px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .pv-status {
            display: none;
        }

        .breakdown-row {
            grid-template-columns: 72px 1fr 34px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# HELPERS
# =========================================================

EVENT_LABELS = {
    "DRIVE": "Drive",
    "PASS": "Pass",
    "CROSS": "Cross",
    "SHOT": "Shot",
    "OUT": "Ball Out",
    "BALL PLAYER BLOCK": "Player / Ball Block",
}

EVENT_ICONS = {
    "DRIVE": "↗",
    "PASS": "→",
    "CROSS": "↗",
    "SHOT": "●",
    "OUT": "↪",
    "BALL PLAYER BLOCK": "◆",
}


def event_label(event_class):
    return EVENT_LABELS.get(event_class, event_class.replace("_", " ").title())


def event_icon(event_class):
    return EVENT_ICONS.get(event_class, "•")


def format_time(seconds):
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def render_section(title, subtitle=None):
    subtitle_html = (
        f'<div class="pv-section-subtitle">{subtitle}</div>'
        if subtitle
        else ""
    )
    st.markdown(
        f"""
        <div class="pv-section">
            <div class="pv-section-title">{title}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric(label, value, description):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-description">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_event_card(event):
    event_class = event["class"]
    score = float(event["score"])
    st.markdown(
        f"""
        <div class="event-card">
            <div>
                <span class="event-time">{event["mmss"]}</span>
                &nbsp;&nbsp;
                <span class="event-name">
                    {event_icon(event_class)} {event_label(event_class)}
                </span>
            </div>
            <div class="event-confidence">
                Confidence {score:.0%}
            </div>
            <div class="confidence-track">
                <div class="confidence-fill" style="width:{score * 100:.1f}%"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_key_moments(events, limit=6):
    """Select high-confidence events for the user-facing highlights view."""
    if not events:
        return []

    ranked = sorted(
        events,
        key=lambda event: float(event.get("score", 0)),
        reverse=True,
    )

    selected = []
    selected_times = []

    for event in ranked:
        time_s = float(event.get("time_s", 0))

        # Avoid filling the highlights with duplicate detections
        # occurring at essentially the same timestamp.
        if any(abs(time_s - existing) < 3 for existing in selected_times):
            continue

        selected.append(event)
        selected_times.append(time_s)

        if len(selected) >= limit:
            break

    return sorted(selected, key=lambda event: float(event.get("time_s", 0)))


def render_breakdown(class_counts, total_events):
    if not class_counts or not total_events:
        st.markdown(
            '<div class="empty-state">No event classes detected.</div>',
            unsafe_allow_html=True,
        )
        return

    max_count = max(class_counts.values())

    for event_class, count in sorted(
        class_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        width = (count / max_count) * 100 if max_count else 0
        st.markdown(
            f"""
            <div class="breakdown-row">
                <div class="breakdown-label">
                    {event_label(event_class)}
                </div>
                <div class="breakdown-track">
                    <div class="breakdown-fill" style="width:{width:.1f}%"></div>
                </div>
                <div class="breakdown-count">{count}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# HEADER
# =========================================================

st.markdown(
    """
    <div class="pv-topbar">
        <div class="pv-brand-wrap">
            <div class="pv-logo">⚽</div>
            <div>
                <div class="pv-brand">PitchVision</div>
                <div class="pv-tagline">Football intelligence powered by computer vision</div>
            </div>
        </div>
        <div class="pv-status">AI EVENT SPOTTING</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# SIDEBAR — ADVANCED ANALYSIS SETTINGS
# =========================================================

with st.sidebar:
    st.markdown("## ⚙️ Analysis Settings")
    st.caption("Advanced controls. Default settings are suitable for normal use.")

    checkpoint_path = st.text_input(
        "Model checkpoint",
        value=os.path.join(
            PROJECT_ROOT,
            "model",
            "results",
            "checkpoints",
            "v3_ckpt_W7_seed0.pt",
        ),
        help="Path to the trained PitchVision v3 checkpoint.",
    )

    threshold = st.slider(
        "Detection threshold",
        min_value=0.1,
        max_value=0.9,
        value=0.5,
        step=0.05,
        help="Higher values show fewer, more confident detections.",
    )

    max_seconds = st.number_input(
        "Maximum duration",
        min_value=0,
        value=0,
        step=30,
        help="0 = process the complete video.",
    )

    st.divider()
    st.caption("PitchVision AI League 2026")
    st.caption("Football event spotting and match insights")

# =========================================================
# HERO
# =========================================================

st.markdown(
    """
    <div class="pv-hero">
        <div class="pv-eyebrow">MATCH INTELLIGENCE</div>
        <div class="pv-title">Turn football footage into searchable insights.</div>
        <div class="pv-description">
            Upload a match recording or use a YouTube link. PitchVision identifies
            football events and organizes them into a timeline you can explore.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# MATCH FOOTAGE INPUT
# =========================================================

render_section(
    "Start a match analysis",
    "Upload a recording or provide a YouTube link",
)

input_tab1, input_tab2 = st.tabs(["📁 Upload video", "▶ YouTube link"])

with input_tab1:
    st.markdown(
        """
        <div class="upload-card">
            <div class="upload-icon">🎥</div>
            <div class="upload-title">Upload match footage</div>
            <div class="upload-copy">
                MP4, MOV, AVI or MKV · Use a clear full-match recording when possible
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_video = st.file_uploader(
        "Choose video",
        type=["mp4", "mov", "avi", "mkv"],
        help="Upload a football match recording from your computer.",
        key="uploaded_match_video",
        label_visibility="collapsed",
    )

with input_tab2:
    youtube_url = st.text_input(
        "YouTube video URL",
        placeholder="https://www.youtube.com/watch?v=...",
        help="Paste the URL of a publicly accessible YouTube match video.",
        key="youtube_match_url",
    )

    if youtube_url:
        st.info(
            "The YouTube video will be downloaded temporarily when you click "
            "**Analyze Match**."
        )

if uploaded_video is None and not youtube_url:
    st.markdown(
        """
        <div class="empty-state">
            <strong>Ready when you are.</strong><br>
            Add match footage above to begin.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# =========================================================
# INPUT PREVIEW + ANALYZE
# =========================================================

render_section("Match footage", "Review the source before analysis")

if uploaded_video is not None:
    source_name = uploaded_video.name
    st.caption(f"Selected file · {source_name}")
    st.video(uploaded_video)
else:
    source_name = youtube_url
    st.caption("Selected YouTube source")
    st.video(youtube_url)

if st.button(
    "🔍 Analyze Match",
    type="primary",
    use_container_width=True,
):
    if not os.path.exists(checkpoint_path):
        st.error("The PitchVision model checkpoint could not be found.")
        st.info(f"Expected checkpoint: `{checkpoint_path}`")
        st.stop()

    with tempfile.TemporaryDirectory() as temp_dir:

        # =====================================================
        # PREPARE VIDEO INPUT
        # =====================================================

        if uploaded_video is not None:
            video_path = os.path.join(
                temp_dir,
                uploaded_video.name,
            )

            with open(video_path, "wb") as f:
                f.write(uploaded_video.getbuffer())

            video_source = uploaded_video.name

        else:
            with st.spinner("Preparing the YouTube match video..."):
                try:
                    video_path = download_youtube_video(
                        youtube_url,
                        temp_dir,
                    )
                    video_source = youtube_url
                except Exception as e:
                    st.error("Could not retrieve the YouTube video.")
                    with st.expander("Technical details"):
                        st.exception(e)
                    st.stop()

        output_dir = os.path.join(
            temp_dir,
            "output",
        )

        duration = (
            None
            if max_seconds == 0
            else max_seconds
        )

        # =====================================================
        # RUN THE EXISTING MODEL PIPELINE
        # =====================================================

        with st.spinner(
            "PitchVision is analyzing the match. This may take a while..."
        ):
            try:
                result = run_inference(
                    video_path=video_path,
                    ckpt_path=checkpoint_path,
                    out_dir=output_dir,
                    threshold=threshold,
                    max_seconds=duration,
                )
            except Exception as e:
                st.error("PitchVision could not complete the analysis.")
                with st.expander("Technical details"):
                    st.exception(e)
                st.stop()

        # =====================================================
        # STORE RESULTS FOR CURRENT SESSION
        # =====================================================

        timeline = result["timeline"]
        events = timeline.get("events", [])

        st.session_state["timeline"] = timeline
        st.session_state["events"] = events
        st.session_state["result"] = result
        st.session_state["source_name"] = source_name
        st.session_state["video_source"] = video_source

        st.success("Analysis complete.")
        st.rerun()

# =========================================================
# DISPLAY RESULTS
# =========================================================

if "events" not in st.session_state:
    st.info("Click **Analyze Match** to generate the PitchVision analysis.")
    st.stop()

events = st.session_state["events"]
timeline = st.session_state["timeline"]
result = st.session_state["result"]

source_name = st.session_state.get("source_name", "Match video")

# =========================================================
# MATCH OVERVIEW
# =========================================================

class_counts = Counter(
    event["class"]
    for event in events
)

unique_classes = len(class_counts)

avg_confidence = (
    sum(float(event["score"]) for event in events) / len(events)
    if events
    else 0
)

last_time = (
    max(float(event["time_s"]) for event in events)
    if events
    else 0
)

duration_text = format_time(last_time) if events else "N/A"

render_section(
    "Match overview",
    f"Analysis generated from {source_name}",
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    render_metric(
        "Events",
        len(events),
        "Detected football moments",
    )

with col2:
    render_metric(
        "Event types",
        unique_classes,
        "Distinct action classes",
    )

with col3:
    render_metric(
        "Passes",
        class_counts.get("PASS", 0),
        "Detected passing actions",
    )

with col4:
    render_metric(
        "Shots",
        class_counts.get("SHOT", 0),
        "Detected shot events",
    )

# Keep confidence available without making it the primary product metric.
with st.expander("Analysis quality details"):
    quality_col1, quality_col2 = st.columns(2)

    with quality_col1:
        st.metric("Average model confidence", f"{avg_confidence:.0%}")

    with quality_col2:
        st.metric("Last detected event", duration_text)

# =========================================================
# VIDEO + KEY MOMENTS
# =========================================================

render_section(
    "Match workspace",
    "Review the footage and jump to the most notable detections",
)

video_col, moments_col = st.columns(
    [1.7, 1],
    gap="large",
)

with video_col:
    st.markdown(
        '<div class="pv-card pv-card-tight">',
        unsafe_allow_html=True,
    )

    st.caption(source_name)

    video_source = st.session_state.get("video_source")

    if uploaded_video is not None:
        st.video(uploaded_video)
    elif video_source:
        st.video(video_source)
    else:
        st.video(youtube_url)

    st.markdown("</div>", unsafe_allow_html=True)

with moments_col:
    key_moments = get_key_moments(events)

    if key_moments:
        for index, event in enumerate(key_moments):
            event_class = event["class"]
            score = float(event["score"])

            st.markdown(
                f"""
                <div class="moment-card">
                    <div class="moment-time">{event["mmss"]}</div>
                    <div class="moment-title">
                        {event_icon(event_class)} {event_label(event_class)}
                    </div>
                    <div class="moment-meta">
                        High-confidence detection · {score:.0%}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Streamlit buttons are deliberately kept separate from the HTML
            # card so they remain native and reliable.
            if st.button(
                "▶ Watch moment",
                key=f"moment_{index}_{event['time_s']}",
                use_container_width=True,
            ):
                st.info(
                    f"Selected {event_label(event_class)} at {event['mmss']}. "
                    "Timestamp-linked playback can be added in the next interaction layer."
                )
    else:
        st.markdown(
            '<div class="empty-state">No key moments were detected.</div>',
            unsafe_allow_html=True,
        )

# =========================================================
# EVENT BREAKDOWN
# =========================================================

breakdown_col, quality_col = st.columns(
    [1.5, 1],
    gap="large",
)

with breakdown_col:
    render_section(
        "Event breakdown",
        "What PitchVision detected",
    )

    render_breakdown(
        class_counts,
        len(events),
    )

with quality_col:
    render_section(
        "Analysis snapshot",
        "At a glance",
    )

    st.markdown(
        '<div class="pv-card">',
        unsafe_allow_html=True,
    )

    if events:
        strongest = max(
            events,
            key=lambda event: float(event["score"]),
        )

        st.markdown(
            f"""
            <div class="metric-label">Highest-confidence detection</div>
            <div class="metric-value">{float(strongest["score"]):.0%}</div>
            <div class="metric-description">
                {event_label(strongest["class"])} at {strongest["mmss"]}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="metric-label">Timeline span</div>
            <div class="metric-value">{duration_text}</div>
            <div class="metric-description">
                Last detected event
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:
        st.markdown(
            '<div class="empty-state">No events available.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# EVENT EXPLORER
# =========================================================

render_section(
    "Event explorer",
    "Search and filter detected moments",
)

filter_col, search_col = st.columns(
    [1, 2],
)

with filter_col:
    event_options = ["All events"] + sorted(class_counts.keys())

    selected_class = st.selectbox(
        "Event type",
        event_options,
        format_func=lambda value: (
            value
            if value == "All events"
            else event_label(value)
        ),
    )

with search_col:
    search_term = st.text_input(
        "Search events",
        placeholder="Search pass, shot, drive...",
    )

filtered_events = events

if selected_class != "All events":
    filtered_events = [
        event
        for event in filtered_events
        if event["class"] == selected_class
    ]

if search_term:
    term = search_term.lower().strip()
    filtered_events = [
        event
        for event in filtered_events
        if term in event["class"].lower()
        or term in event_label(event["class"]).lower()
    ]

st.caption(
    f"Showing {len(filtered_events)} of {len(events)} detected events"
)

# =========================================================
# TIMELINE / EVENT LIST
# =========================================================

if filtered_events:
    timeline_col, detail_col = st.columns(
        [1.55, 1],
        gap="large",
    )

    with timeline_col:
        render_section(
            "Match timeline",
            "Detected moments in match order",
        )

        # Limit the initial view so the page does not become a wall of 71 cards.
        display_limit = 12
        visible_events = filtered_events[:display_limit]

        for index, event in enumerate(visible_events):
            render_event_card(event)

            if st.button(
                f"▶ Select {event['mmss']}",
                key=f"event_select_{index}_{event['time_s']}_{event['class']}",
                use_container_width=True,
            ):
                st.session_state["selected_event"] = event
                st.rerun()

        if len(filtered_events) > display_limit:
            st.info(
                f"{len(filtered_events) - display_limit} more events are available "
                "in the detailed table below."
            )

    with detail_col:
        render_section(
            "Selected event",
            "Event details",
        )

        selected_event = st.session_state.get("selected_event")

        if selected_event:
            st.markdown(
                f"""
                <div class="pv-card">
                    <div class="event-time">
                        {selected_event["mmss"]}
                    </div>
                    <div class="pv-title" style="font-size:1.45rem; margin-top:.35rem;">
                        {event_icon(selected_event["class"])}
                        {event_label(selected_event["class"])}
                    </div>
                    <div class="event-confidence" style="margin-top:.45rem;">
                        Model confidence: {float(selected_event["score"]):.0%}
                    </div>
                    <div class="confidence-track">
                        <div class="confidence-fill"
                             style="width:{float(selected_event["score"]) * 100:.1f}%">
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.write("")
            st.button(
                f"▶ Watch from {selected_event['mmss']}",
                use_container_width=True,
                key="watch_selected_event",
            )
            st.caption(
                "The current Streamlit video component does not expose "
                "timestamp seeking from these event cards. The selected "
                "timestamp is retained so we can wire playback control next."
            )
        else:
            st.markdown(
                """
                <div class="empty-state">
                    Select an event to inspect its details.
                </div>
                """,
                unsafe_allow_html=True,
            )

else:
    st.markdown(
        '<div class="empty-state">No events match the current filters.</div>',
        unsafe_allow_html=True,
    )

# =========================================================
# DETAILED EVENTS
# =========================================================

render_section(
    "Detailed event data",
    "Useful for analysts and technical review",
)

if filtered_events:
    table_data = [
        {
            "Time": event["mmss"],
            "Event": event_label(event["class"]),
            "Confidence": f"{float(event['score']):.1%}",
        }
        for event in filtered_events
    ]

    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No events to display.")

# =========================================================
# EXPORT
# =========================================================

render_section(
    "Export results",
    "Take the match data with you",
)

download_col1, download_col2 = st.columns(2)

with download_col1:
    timeline_json = json.dumps(
        timeline,
        indent=2,
    )

    st.download_button(
        "⬇️ Download timeline JSON",
        data=timeline_json,
        file_name="pitchvision_timeline.json",
        mime="application/json",
        use_container_width=True,
    )

with download_col2:
    csv_lines = ["time_s,mmss,class,score"]

    for event in events:
        csv_lines.append(
            f"{event['time_s']},"
            f"{event['mmss']},"
            f"{event['class']},"
            f"{event['score']}"
        )

    csv_data = "\n".join(csv_lines)

    st.download_button(
        "⬇️ Download events CSV",
        data=csv_data,
        file_name="pitchvision_events.csv",
        mime="text/csv",
        use_container_width=True,
    )

# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="pv-footer">
        PitchVision · AI-powered football event spotting · PARC 2026
    </div>
    """,
    unsafe_allow_html=True,
)
