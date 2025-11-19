import streamlit as st
import google.generativeai as genai
import json
from docx import Document

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="LegalMatch AI - Comparateur de Contrats",
    page_icon="⚖️",
    layout="wide"
)

# --- CSS PERSONNALISÉ (STYLE) ---
st.markdown("""
<style>
    .report-box { padding: 15px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid; }
    .cat-EXACT { background-color: #dcfce7; border-color: #22c55e; color: #166534; }
    .cat-ADDED { background-color: #fee2e2; border-color: #ef4444; color: #991b1b; }
    .cat-MISSING { background-color: #f3f4f6; border-color: #6b7280; color: #374151; opacity: 0.8; }
    .cat-MOVED { background-color: #dbeafe; border-color: #3b82f6; color: #1e40af; }
    .cat-MODIFIED { background-color: #fef9c3; border-color: #eab308; color: #854d0e; }
    .diff-add { background-color: #fca5a5; font-weight: bold; text-decoration: none; padding: 0 2px; border-radius: 2px; }
    .diff-del { text-decoration: line-through; color: #dc2626; opacity: 0.7; margin-right: 4px;}
    .tooltip { font-size: 0.8em; color: #666; margin-bottom: 5px; text-transform: uppercase; font-weight: bold; }
    .stFileUploader { padding-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- FONCTION D'EXTRACTION DU TEXTE WORD ---
def extract_text_from_docx(uploaded_file):
    """Lit un fichier .docx et retourne le texte brut."""
    try:
        doc = Document(uploaded_file)
        full_text = []
        for para in doc.paragraphs:
            # On ne garde que les paragraphes non vides pour nettoyer un peu
            if para.text.strip():
                full_text.append(para.text)
        return '\n\n'.join(full_text)
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier : {e}")
        return None

# --- SIDEBAR : CONFIGURATION ---
with st.sidebar:
    st.title("⚙️ Configuration")
    api_key = st.text_input("Clé API Gemini", type="password")
    st.info("Nécessite une clé [Google AI Studio](https://aistudio.google.com/).")
    st.divider()
    st.markdown("### Légende")
    st.markdown("🟢 **Identique**")
    st.markdown("🟡 **Modifié** (Attention requise)")
    st.markdown("🔴 **Ajouté** (Nouveau dans V2)")
    st.markdown("🔵 **Déplacé**")
    st.markdown("⚪ **Supprimé**")

# --- FONCTION PRINCIPALE GEMINI ---
def analyze_contracts(text_v1, text_v2, api_key):
    genai.configure(api_key=api_key)
    
    generation_config = {
        "temperature": 0.1, # Température basse pour plus de rigueur
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )

    # Le Prompt Système reste le même
    system_prompt = """
    Tu es un expert juridique. Compare les deux textes suivants (V1 et V2).
    Retourne UNIQUEMENT un JSON respectant strictement cette structure :
    {
      "comparisonData": [
        {
          "id": number,
          "category": "EXACT" | "MISSING" | "ADDED" | "MOVED" | "MODIFIED",
          "similarityScore": number (0-100),
          "textV1": "string (contenu original si existe)",
          "textV2": "string (contenu final si existe)",
          "annotatedDiffV2": "string (Texte V2 avec balises HTML <span class='diff-add'>...</span> pour les ajouts et <span class='diff-del'>...</span> pour les suppressions)",
          "originalPositionV1": number (si applicable)
        }
      ],
      "legalAnalysis": {
        "obsoleteLaws": [{ "sourceDoc": "V1"|"V2", "quote": "string", "issue": "string", "suggestion": "string" }],
        "internalContradictions": [{ "doc": "string", "clause": "string", "explanation": "string" }],
        "interDocContradictions": [{ "clauseV1": "string", "clauseV2": "string", "conflictDescription": "string" }]
      }
    }
    """
    
    user_message = f"--- DOCUMENT V1 (Origine) ---\n{text_v1}\n\n--- DOCUMENT V2 (Final) ---\n{text_v2}"

    with st.spinner("🤖 Lecture et Analyse juridique en cours..."):
        response = model.generate_content([system_prompt, user_message])
        return json.loads(response.text)

# --- INTERFACE UTILISATEUR PRINCIPALE ---
st.title("⚖️ Comparateur Légal Intelligent")
st.markdown("Téléchargez vos contrats au format **.docx** pour lancer l'analyse.")

col1, col2 = st.columns(2)

# Gestion V1
with col1:
    st.subheader("1. Contrat de Réservation (V1)")
    file_v1 = st.file_uploader("Déposer le fichier V1", type=["docx"], key="v1")
    text_v1 = ""
    if file_v1:
        text_v1 = extract_text_from_docx(file_v1)
        if text_v1:
            st.success(f"V1 chargé : {len(text_v1)} caractères.")

# Gestion V2
with col2:
    st.subheader("2. Acte de Vente Final (V2)")
    file_v2 = st.file_uploader("Déposer le fichier V2", type=["docx"], key="v2")
    text_v2 = ""
    if file_v2:
        text_v2 = extract_text_from_docx(file_v2)
        if text_v2:
            st.success(f"V2 chargé : {len(text_v2)} caractères.")

# Bouton d'action
start_analysis = st.button("Lancer l'Analyse Comparative", type="primary", use_container_width=True)

if start_analysis:
    if not api_key:
        st.error("⚠️ Clé API manquante.")
    elif not text_v1 or not text_v2:
        st.warning("⚠️ Veuillez charger les deux documents .docx avant de lancer l'analyse.")
    else:
        try:
            data = analyze_contracts(text_v1, text_v2, api_key)
            st.session_state['analysis_result'] = data
        except Exception as e:
            st.error(f"Une erreur est survenue : {e}")

# --- AFFICHAGE DES RÉSULTATS (Identique à la version précédente) ---
if 'analysis_result' in st.session_state:
    data = st.session_state['analysis_result']
    comp_data = data.get("comparisonData", [])
    legal_data = data.get("legalAnalysis", {})

    st.divider()
    tab1, tab2, tab3 = st.tabs(["📄 Vue Documentaire Annotée", "🔍 Vue Comparative (Diff)", "⚖️ Risques Légaux"])

    # VUE 1 : TEXTE COMPLET V2 ANNOTÉ
    with tab1:
        st.markdown("### Document V2 reconstitué avec annotations")
        for item in comp_data:
            if item['category'] == 'MISSING': continue
            
            cat = item['category']
            content = item.get('annotatedDiffV2', item['textV2']) if cat == 'MODIFIED' else item['textV2']
            similarity = f"<span style='float:right; font-size:0.8em'>Similarité: {item['similarityScore']}%</span>" if item.get('similarityScore') else ""
            
            st.markdown(f"""
            <div class="report-box cat-{cat}">
                <div class="tooltip">{cat} {similarity}</div>
                <div>{content}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Section des éléments supprimés à la fin
        missing = [x for x in comp_data if x['category'] == 'MISSING']
        if missing:
            st.markdown("#### 🗑️ Éléments présents en V1 mais supprimés de V2")
            for item in missing:
                st.markdown(f"""<div class="report-box cat-MISSING"><div>{item['textV1']}</div></div>""", unsafe_allow_html=True)

    # VUE 2 : COMPARAISON CÔTE À CÔTE
    with tab2:
        filter_cat = st.radio("Filtrer :", ["MODIFIED", "ADDED", "MISSING", "MOVED"], horizontal=True)
        items = [x for x in comp_data if x['category'] == filter_cat]
        
        if not items:
            st.info("Aucun élément dans cette catégorie.")
        
        for item in items:
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Version V1")
                st.text_area(label="v1", value=item.get('textV1', 'N/A'), height=150, disabled=True, key=f"v1_{item['id']}")
            with c2:
                st.caption("Version V2")
                diff_html = item.get('annotatedDiffV2', item.get('textV2', 'N/A'))
                st.markdown(f"<div class='cat-{filter_cat}' style='padding:10px; height:150px; overflow-y:auto; border-radius:5px'>{diff_html}</div>", unsafe_allow_html=True)
            st.markdown("---")

    # VUE 3 : ANALYSE LÉGALE
    with tab3:
        st.subheader("Lois Obsolètes")
        for law in legal_data.get('obsoleteLaws', []):
            st.warning(f"**{law['sourceDoc']}**: \"{law['quote']}\" -> {law['issue']} (Suggestion: {law['suggestion']})")
        
        st.subheader("Contradictions")
        for conflict in legal_data.get('interDocContradictions', []):
            st.error(f"Conflit entre V1/V2 : {conflict['conflictDescription']}")

