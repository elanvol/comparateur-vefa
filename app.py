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

# --- CSS PERSONNALISÉ ---
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

# --- FONCTIONS UTILITAIRES ---

def extract_text_from_docx(uploaded_file):
    """Lit un fichier .docx et retourne le texte brut."""
    try:
        doc = Document(uploaded_file)
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text)
        return '\n\n'.join(full_text)
    except Exception as e:
        st.error(f"Erreur de lecture du fichier : {e}")
        return None

def get_best_available_model(api_key):
    """
    Détecte automatiquement le meilleur modèle disponible pour cette clé API.
    Ordre de préférence : 1.5-Pro > 1.5-Flash > 1.0-Pro
    """
    try:
        genai.configure(api_key=api_key)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Logique de priorité
        if any('gemini-1.5-pro' in m for m in available_models):
            return 'gemini-1.5-pro'
        elif any('gemini-1.5-flash' in m for m in available_models):
            return 'gemini-1.5-flash'
        elif any('gemini-pro' in m for m in available_models):
            return 'gemini-pro'
        else:
            # Retourne le premier modèle disponible par défaut ou une erreur
            return available_models[0] if available_models else None
    except Exception as e:
        # Si la clé est invalide, list_models va planter
        return None

# --- FONCTION PRINCIPALE D'ANALYSE ---

def analyze_contracts(text_v1, text_v2, api_key):
    # 1. Trouver le modèle
    model_name = get_best_available_model(api_key)
    
    if not model_name:
        raise ValueError("Impossible de trouver un modèle Gemini ou Clé API invalide.")
        
    st.toast(f"Modèle utilisé : {model_name}", icon="🤖") # Feedback utilisateur
    
    genai.configure(api_key=api_key)
    
    generation_config = {
        "temperature": 0.1,
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=generation_config,
    )

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

    response = model.generate_content([system_prompt, user_message])
    return json.loads(response.text)

# --- INTERFACE UTILISATEUR ---
with st.sidebar:
    st.title("⚙️ Configuration")
    api_key = st.text_input("Clé API Gemini", type="password")
    st.info("Si vous avez une erreur, vérifiez que votre clé est active sur Google AI Studio.")
    st.divider()
    st.markdown("### Légende")
    st.markdown("🟢 **Identique**")
    st.markdown("🟡 **Modifié**")
    st.markdown("🔴 **Ajouté**")
    st.markdown("🔵 **Déplacé**")
    st.markdown("⚪ **Supprimé**")

st.title("⚖️ Comparateur Légal Intelligent")
st.markdown("Téléchargez vos contrats au format **.docx** (Word) pour lancer l'analyse.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Contrat de Réservation (V1)")
    file_v1 = st.file_uploader("Fichier V1", type=["docx"], key="v1")
    text_v1 = extract_text_from_docx(file_v1) if file_v1 else ""
    if text_v1: st.success(f"V1: {len(text_v1)} caractères")

with col2:
    st.subheader("2. Acte de Vente Final (V2)")
    file_v2 = st.file_uploader("Fichier V2", type=["docx"], key="v2")
    text_v2 = extract_text_from_docx(file_v2) if file_v2 else ""
    if text_v2: st.success(f"V2: {len(text_v2)} caractères")

start_analysis = st.button("Lancer l'Analyse Comparative", type="primary", use_container_width=True)

if start_analysis:
    if not api_key:
        st.error("⚠️ Clé API manquante.")
    elif not text_v1 or not text_v2:
        st.warning("⚠️ Veuillez charger les deux documents.")
    else:
        with st.spinner("🤖 Recherche du meilleur modèle et Analyse en cours..."):
            try:
                data = analyze_contracts(text_v1, text_v2, api_key)
                st.session_state['analysis_result'] = data
            except Exception as e:
                st.error(f"Erreur technique : {e}")

# --- VISUALISATION DES RÉSULTATS ---
if 'analysis_result' in st.session_state:
    data = st.session_state['analysis_result']
    comp_data = data.get("comparisonData", [])
    legal_data = data.get("legalAnalysis", {})

    st.divider()
    tab1, tab2, tab3 = st.tabs(["📄 Vue Annotée", "🔍 Différences", "⚖️ Analyse Légale"])

    # VUE 1
    with tab1:
        st.caption("Ce document est une reconstruction du texte V2 incluant les codes couleurs.")
        for item in comp_data:
            if item['category'] == 'MISSING': continue
            cat = item['category']
            content = item.get('annotatedDiffV2', item['textV2']) if cat == 'MODIFIED' else item['textV2']
            sim = f"- Sim: {item['similarityScore']}%" if item.get('similarityScore') else ""
            
            # CORRECTION ICI : Utilisation de simple quotes pour l'HTML à l'intérieur du f-string
            st.markdown(f"""
            <div class='report-box cat-{cat}'>
                <div class='tooltip'>{cat} {sim}</div>
                <div>{content}</div>
            </div>""", unsafe_allow_html=True)
        
        missing = [x for x in comp_data if x['category'] == 'MISSING']
        if missing:
            st.markdown("#### 🗑️ Clauses supprimées (Présentes en V1 uniquement)")
            for item in missing:
                # CORRECTION ICI ÉGALEMENT
                st.markdown(f"<div class='report-box cat-MISSING'><div>{item['textV1']}</div></div>", unsafe_allow_html=True)

    # VUE 2
    with tab2:
        filter_cat = st.radio("Filtrer :", ["MODIFIED", "ADDED", "MISSING", "MOVED"], horizontal=True)
        items = [x for x in comp_data if x['category'] == filter_cat]
        if not items: st.info("Aucun élément.")
        for item in items:
            c1, c2 = st.columns(2)
            with c1: st.info(item.get('textV1', 'N/A'))
            with c2: 
                diff = item.get('annotatedDiffV2', item.get('textV2', 'N/A'))
                st.markdown(f"<div class='cat-{filter_cat}' style='padding:10px'>{diff}</div>", unsafe_allow_html=True)
            st.markdown("---")

    # VUE 3
    with tab3:
        st.subheader("Alertes Légales")
        if not legal_data.get('obsoleteLaws') and not legal_data.get('interDocContradictions'):
            st.success("R.A.S : Aucune alerte majeure détectée.")
            
        for law in legal_data.get('obsoleteLaws', []):
            st.warning(f"**Loi Obsolète ({law['sourceDoc']})**: {law['issue']}\n> {law['quote']}")
        
        for conflict in legal_data.get('interDocContradictions', []):
            st.error(f"**Conflit V1 vs V2** : {conflict['conflictDescription']}")
