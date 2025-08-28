import sys

from pathlib import Path

# Ensure the app directory is in the Python path
ROOT = Path(__file__).resolve().parents[1]  # project root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import datetime
import streamlit as st

try:
    from audio_recorder_streamlit import audio_recorder
    RECORDER_AVAILABLE = True
except Exception as _e:
    RECORDER_AVAILABLE = False
    RECORDER_IMPORT_ERROR = str(_e)

from app.config import RETRIEVER_TOP_K, TTS_VOICE, TTS_VOICE_CHOICES, MIC_DIR
from app.rag.retriever import BooksRetriever
from app.rag.prompts import make_recommendation_messages
from app.llm.openai_client import chat_once
from app.tools.summary_tool import call_summary_tool_via_openai
from app.guards.moderation import check_message
from app.tools.tts import synthesize_to_file, make_tts_key
from app.tools.stt import transcribe_wav, transcribe_bytes


# Helper function to format candidates as a Markdown table
def candidates_markdown(items):
    lines = ["| # | Title | Distance |", "|---:|---|---:|"]
    for i, it in enumerate(items, 0):
        dist = it.get("distance")
        dist_s = f"{dist:.4f}" if isinstance(dist, (int, float)) else "n/a"
        title = (it.get("title") or "").replace("|", "\\|")  # escape pipes
        lines.append(f"| {i} | {title} | {dist_s} |")
    return "\n".join(lines)

# Streamlit app configuration
st.set_page_config(page_title="Smart Librarian", page_icon="📚", layout="centered")
st.title("📚 Smart Librarian")
st.caption("Tell me what you're in the mood for. I'll recommend one book.")

# Sessions state (history for display only; not used as LLM context) ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "last_title" not in st.session_state:
    st.session_state["last_title"] = None
if "last_item" not in st.session_state:
    st.session_state["last_item"] = None
if "last_rec_text" not in st.session_state:
    st.session_state["last_rec_text"] = None
if "last_summary_text" not in st.session_state:
    st.session_state["last_summary_text"] = None
if "last_debug" not in st.session_state:
    st.session_state["last_debug"] = None

# Sidebar for actions
st.sidebar.header("Actions")

# Clear chat button (resets session state)
st.sidebar.button(
    "Clear chat",
    on_click=lambda: (st.session_state.update(messages=[], 
                                              last_title=None, 
                                              last_item=None,
                                              last_rec_text=None,
                                              last_summary_text=None,
                                              last_debug=None)
                    ),
)

st.sidebar.divider()

# Voice selector (persist in session)
st.sidebar.subheader("Choose a voice")

default_voice = st.session_state.get("tts_voice", TTS_VOICE)
try:
    default_idx = TTS_VOICE_CHOICES.index(default_voice)
except ValueError:
    default_idx = 0
voice = st.sidebar.selectbox("Voice list dropdown", TTS_VOICE_CHOICES, index=default_idx, key="tts_voice")

st.sidebar.divider()

# Voice mode toggle
st.sidebar.subheader("🎧 Voice mode")
voice_mode = st.sidebar.toggle("Enable voice mode", value=False, key="voice_mode_toggle")

# Session buffer for mic
if "last_transcript" not in st.session_state:
    st.session_state["last_transcript"] = ""
if "transcript_area" not in st.session_state:
    st.session_state["transcript_area"] = ""

if voice_mode:
    audio_bytes = None
    if RECORDER_AVAILABLE:
        try:
            # This is the only line that uses a custom component.
            audio_bytes = audio_recorder(pause_threshold=2.0, sample_rate=16000, text="")
        except Exception as e:
            # PyArrow / components blocked -> soft fallback
            st.sidebar.warning("Microphone recorder unavailable on this machine. Falling back to upload.")
            st.sidebar.caption(f"(Detail: {type(e).__name__})")
            audio_bytes = None
    else:
        st.sidebar.info("Recorder component not available. Use file upload below.")

    if audio_bytes:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        wav_path = (MIC_DIR / f"mic_{ts}.wav").resolve()
        wav_path.write_bytes(audio_bytes)

        try:
            text = transcribe_bytes(audio_bytes, filename="mic.wav", language="en")
            st.session_state["last_transcript"] = text
            st.session_state["transcript_area"] = text
            st.sidebar.success("Transcribed microphone audio.")
            st.sidebar.audio(audio_bytes, format="audio/wav")
            st.rerun()
        except Exception as e:
            st.session_state["last_transcript"] = ""
            st.sidebar.warning(f"STT failed: {e}")

     # Upload fallback (works even when components are blocked)
    up = st.sidebar.file_uploader("Upload audio (wav/mp3/m4a/webm)", type=["wav", "mp3", "m4a", "webm"])
    if st.sidebar.button("Transcribe upload", use_container_width=True, key="btn_stt_upload"):
        if up:
            from app.tools.stt import transcribe_bytes
            try:
                txt = transcribe_bytes(up.read(), filename=up.name, language="en")
                st.session_state["last_transcript"] = txt
                st.session_state["transcript_area"] = txt
                st.sidebar.success("Transcribed uploaded file.")
                st.rerun()
            except Exception as e:
                st.sidebar.warning(f"STT failed: {e}")
        else:
            st.sidebar.warning("Please choose a file first.")

    st.sidebar.divider()
     # Always show editable transcript + “Use this text”
    st.sidebar.text_area(
        "Transcript (edit before sending):",
        key="transcript_area",
        height=120,
    )
    if st.sidebar.button("↩︎ Use this text", use_container_width=True, key="btn_use_transcript"):
        st.session_state["inject_user_text"] = st.session_state["transcript_area"].strip()
        st.rerun()
   

# Render chat history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Chat inpit: always render ---
typed_now = st.chat_input("e.g., 'I want a story about friendship and magic'")

# Decide what to process this run
user_query = None
pending = st.session_state.pop("inject_user_text", None)
if pending:
    user_query = pending
elif typed_now:
    user_query = typed_now

if user_query:
    with st.chat_message("user"):
        st.markdown(user_query)
    st.session_state["messages"].append({"role": "user", "content": user_query})

    # Moderation guard
    mod = check_message(user_query)
    if mod.flagged:
        polite = "I can’t process messages that include offensive language. Please rephrase your request."
        with st.chat_message("assistant"):
            st.warning(polite)
        st.session_state["messages"].append({"role": "assistant", "content": polite})

        # Surface minimal debug info
        with st.expander("🔎 Debug: moderation"):
            st.markdown(f"**Provider**: {mod.provider}")
            if mod.categories:
                st.markdown(f"**Categories**: {', '.join(mod.categories)}")
            if mod.error:
                st.markdown(f"**Fallback reason**: {mod.error}")
        # Stop before retrieval/LLM work
        st.stop()

    # Retrieval: top-1 only
    retr = BooksRetriever()
    items = retr.search(user_query, top_k=RETRIEVER_TOP_K)

    # If no items found, show a warning
    if not items:
        msg = "I couldn't find a good match. Could you rephrase your request?"
        with st.chat_message("assistant"):
            st.warning(msg)
        st.session_state["messages"].append({"role": "assistant", "content": msg})
        st.session_state["last_debug"] = None
        st.stop()

    best = items[0]
    title = best["title"]
    doc = best["document"]

    # Build messages and write the recommendation (short, EN, no CTA)
    messages = make_recommendation_messages(
        user_query=user_query,
        title=title,
        retrieved_document=doc
    )
    reply = chat_once(messages)
    with st.chat_message("assistant"):
        st.markdown(reply)
    
    # Persist for reruns + history
    st.session_state["last_rec_text"] = reply
    st.session_state["messages"].append({"role": "assistant", "content": reply})

    # Keep last title for tool call
    st.session_state["last_title"] = title
    st.session_state["last_item"] = best

    # AUTO tool call for full summary
    tool_res = call_summary_tool_via_openai(title)
    with st.chat_message("assistant"):
        if tool_res["ok"]:
            full = tool_res["summary"]
            st.markdown(f"**Detailed summary - _{tool_res['args_title']}_**")
            st.write(full)

            # Persist for reruns + history
            st.session_state["last_summary_text"] = full
            st.session_state["messages"].append({
                "role": "assistant",
                "content": f"**Detailed summary — _{tool_res['args_title']}_**\n\n{full}"
            })
        else:
            st.warning(f"Summary not found for **{title}**.")
            st.session_state["last_summary_text"] = None
            st.session_state["last_debug"] = None

    # Persist debug for later reruns
    st.session_state["last_debug"] = {
        "top_title": title,
        "top_doc": doc,
        "candidates": [
            {
                "rank": i + 1,
                "title": it.get("title", ""),
                "distance": it.get("distance"),
            }
            for i, it in enumerate(items)
        ],
    }


# Show debug info and audio playback only if there are messages
if st.session_state["messages"] != []:
    # Debug info expander
    dbg = st.session_state.get("last_debug")
    if dbg:
        with st.expander("🔎 Debug: retrieved candidates & score", expanded=False):
            # simple markdown table
            lines = ["| # | Tttle | Distance |", "|---:|---|---:|"]
            for row in dbg["candidates"]:
                dist = row["distance"]
                dist_s = f"{dist:.4f}" if isinstance(dist, (int, float)) else "n/a"
                t = row["title"].replace("|", "\\|")  # escape pipes
                lines.append(f"| {row['rank']} | {t} | {dist_s} |")

            st.markdown("\n".join(lines))
            st.markdown("**Short summary of top-1 used for LLM:**")
            st.code(dbg["top_doc"])


    # Audio playback for TTS
    with st.expander("🔊 Audio (Text-to-Speech)", expanded=False):
        rec_text = st.session_state.get("last_rec_text")
        sum_text = st.session_state.get("last_summary_text")

        col1, col2 = st.columns(2)

        with col1:
            clicked = st.button("🔊 Listen to recommendation", disabled=not rec_text, key="btn_tts_rec")
            if clicked and rec_text:
                try:
                    p = synthesize_to_file(rec_text, voice=st.session_state.get("tts_voice", TTS_VOICE))
                    st.audio(str(p))
                    st.caption(f"Saved to {p}")
                except Exception as e:
                    st.warning(f"TTS failed: {e}")

        with col2:
            clicked = st.button("🔊 Listen to summary", disabled=not sum_text, key="btn_tts_sum")
            if clicked and sum_text:
                try:
                    p = synthesize_to_file(sum_text, voice=st.session_state.get("tts_voice", TTS_VOICE))
                    st.audio(str(p))
                    st.caption(f"Saved to {p}")
                except Exception as e:
                    st.warning(f"TTS failed: {e}")