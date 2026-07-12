"""
PresciMate - upload a prescription photo, get it explained in your
language, download it as a PDF, and see your past prescriptions
(only yours - login-gated).

Run with: streamlit run app.py
"""
import os

import streamlit as st

import auth
import config
import explain
import extraction
import knowledge_base as kb
import pdf_export
import sarvam_translator
import theme

st.set_page_config(page_title="PresciMate", page_icon="💊", layout="wide")
theme.apply()

username, display_name = auth.require_login()

with st.sidebar:
    st.title("💊 PresciMate")
    st.caption(f"Logged in as {display_name}")
    if st.button("Log out"):
        auth.logout()

    st.divider()
    language = st.selectbox("Explain my prescription in:", list(config.LANGUAGES.keys()))
    language_code = config.LANGUAGES[language]["code"]

    st.divider()
    if "gemini" in (config.OCR_PROVIDER, config.CHAT_PROVIDER):
        st.caption("⚠️ Free tier - Google may review this traffic. See README.")

    st.divider()
    st.info(config.DISCLAIMER)

tab_upload, tab_history = st.tabs(["Upload prescription", "My history"])

# ------------------------------------------------------------------ #
# Upload + explain
# ------------------------------------------------------------------ #
with tab_upload:
    uploaded_file = st.file_uploader("Photo of your prescription", type=["jpg", "jpeg", "png", "webp"])

    if uploaded_file:
        col1, col2 = st.columns([1, 1.4])
        with col1:
            st.image(uploaded_file, use_container_width=True)

        if st.button("Explain my prescription", type="primary"):
            with st.spinner("Reading the prescription..."):
                try:
                    extracted = extraction.extract_prescription(uploaded_file.getvalue(), uploaded_file.name)
                except Exception as e:
                    st.error(str(e))
                    extracted = None

            if extracted and extracted["medicines"]:
                medicines = extracted["medicines"]
                drug_names = [m["name"] for m in medicines]

                with st.spinner("Looking up the medicines and checking interactions..."):
                    drug_context = "\n\n".join(kb.search_drug_knowledge(name) for name in drug_names)
                    interactions = kb.check_interactions(drug_names)

                with st.spinner("Writing the explanation..."):
                    english_explanation = explain.write_explanation(medicines, drug_context, interactions)

                with st.spinner(f"Translating into {language}..."):
                    final_explanation = sarvam_translator.translate(english_explanation, language_code)

                with st.spinner("Saving to your history..."):
                    kb.save_prescription(username, medicines, final_explanation, language)

                st.session_state["last_result"] = {
                    "medicines": medicines,
                    "explanation": final_explanation,
                    "interactions": interactions,
                    "language": language,
                    "low_confidence": extracted.get("low_confidence", False),
                }

        result = st.session_state.get("last_result")
        if result:
            with col2:
                if result["low_confidence"]:
                    st.warning("Handwriting was hard to read in places - please double check against the original.")

                st.subheader("Medicines found")
                for m in result["medicines"]:
                    st.write(f"**{m['name']}** - {m.get('dosage') or ''} {m.get('frequency') or ''} {m.get('duration') or ''}")

                if result["interactions"]:
                    st.subheader("Interaction warnings")
                    for i in result["interactions"]:
                        st.warning(f"**{i['drug_a']} + {i['drug_b']}** ({i['severity']}): {i['description']}")

                st.subheader(f"Explained in {result['language']}")
                st.markdown(result["explanation"])

                pdf_path = f"/tmp/rxsaathi_{username}.pdf"
                pdf_export.build_pdf(pdf_path, result["medicines"], result["explanation"], result["language"])
                with open(pdf_path, "rb") as f:
                    st.download_button("Download as PDF", f, file_name="prescription_explained.pdf", mime="application/pdf")

        # simple follow-up question - just a keyword check for anything
        # urgent, then plain RAG + Claude for everything else
        if result:
            st.divider()
            question = st.text_input("Ask a question about this prescription")
            if question:
                if any(kw in question.lower() for kw in config.EMERGENCY_KEYWORDS):
                    answer = sarvam_translator.translate(config.EMERGENCY_MESSAGE, language_code)
                    st.error(answer)
                else:
                    # include what was actually extracted from THIS
                    # prescription (dosage, frequency, etc.), not just
                    # general info about the drug - otherwise questions
                    # like "what's the dosage" have no answer to draw on
                    prescription_details = "\n".join(
                        f"{m['name']}: dosage={m.get('dosage') or 'not specified'}, "
                        f"frequency={m.get('frequency') or 'not specified'}, "
                        f"duration={m.get('duration') or 'not specified'}, "
                        f"instructions={m.get('instructions') or 'not specified'}"
                        for m in result["medicines"]
                    )
                    general_context = "\n\n".join(kb.search_drug_knowledge(m["name"]) for m in result["medicines"])
                    drug_context = f"From this prescription:\n{prescription_details}\n\nGeneral drug info:\n{general_context}"

                    with st.spinner("Thinking..."):
                        answer_en = explain.answer_question(question, drug_context)
                        answer = sarvam_translator.translate(answer_en, language_code)
                    st.markdown(answer)

# ------------------------------------------------------------------ #
# History - only this user's own prescriptions
# ------------------------------------------------------------------ #
with tab_history:
    st.subheader("Your past prescriptions")
    history = kb.get_user_history(username)

    if not history:
        st.info("No prescriptions yet - upload one in the other tab.")
    else:
        for record in history:
            with st.expander(f"{record.get('created_at', '')[:10]} - {record.get('medicines', '')}"):
                st.markdown(record.get("explanation", ""))
