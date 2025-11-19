import streamlit as st
import google.generativeai as genai
import json
import os

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="LegalMatch AI - Comparateur de Contrats",
    page_icon="⚖️",
    layout="wide"
)

# --- CSS PERSONNALISÉ POUR LES COULEURS (Tailwind-like) ---
st.markdown("""
<style>
    .report-box { padding: 15px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid; }
    
    /* EXACT - Vert */
    .cat-EXACT { background-color: #dcfce7; border-color: #22c55e; color: #166534; }
    
    /* ADDED - Rouge (V2 contient, V1 non) */
    .cat-ADDED { background-color: #fee2e2; border-color: #ef4444; color: #991b1b; }
    
    /* MISSING - Gris (V1 contenait, V2 non) */
    .cat-MISSING { background-color: #f3f4f6; border-color: #6b7280; color: #374151; opacity: 0.8; }
    
    /* MOVED - Bleu */
    .cat-MOVED { background-color: #dbeafe; border-color: #3b82f6; color: #1e40af; }
    
    /* MODIFIED - Jaune */
    .cat-MODIFIED { background-color: #fef9c3; border-color: #eab308; color: #854d0e; }

    /* Highlights pour les diffs */
    .diff-add { background-color: #fca5a5; font-weight: bold; text-decoration: none; padding: 0 2px; border-radius: 2px; }
    .diff-del { text-decoration: line-through; color: #dc2626; opacity: 0.7; margin-right: 4px;}
    
    .tooltip { font-size: 0.8em; color: #666; margin-bottom: 5px; text-transform: uppercase; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR : CONFIGURATION ---
with st.sidebar:
    st.title("⚙️ Configuration")
    api_key = st.text_input("Clé API Gemini (Google AI Studio)", type="password")
    st.info("Obtenez votre clé sur [Google AI Studio](https://aistudio.google.com/).")
    st.markdown("---")
    st.markdown("**Légende :**")
    st.markdown("🟢 **Identique** : Aucun changement")
    st.markdown("🟡 **Modifié** : Changements textuels")
    st.markdown("🔴 **Ajouté** : Nouveau dans V2")
    st.markdown("🔵 **Déplacé** : Changement de position")
    st.markdown("⚪ **Supprimé** : Présent en V1, absent en V2")

# --- FONCTION PRINCIPALE D'ANALYSE ---
def analyze_contracts(text_v1, text_v2, api_key):
    genai.configure(api_key=api_key)
    
    # Configuration du modèle
    generation_config = {
        "temperature": 0.2,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro", # Utilisation du modèle Pro pour le contexte large
        generation_config=generation_config,
    )

    # Prompt Système
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
          "annotatedDiffV2": "string (Texte V2 avec balises HTML <span class='diff-add'>...</span> pour les ajouts et <span class='diff-del'>...</span> pour les suppressions par rapport à V1)",
          "originalPositionV1": number (si applicable)
        }
      ],
      "legalAnalysis": {
        "obsoleteLaws": [{ "sourceDoc": "V1"|"V2", "quote": "string", "issue": "string", "suggestion": "string" }],
        "internalContradictions": [{ "doc": "string", "clause": "string", "explanation": "string" }],
        "interDocContradictions": [{ "clauseV1": "string", "clauseV2": "string", "conflictDescription": "string" }]
      }
    }

    Règles :
    1. Segmente par paragraphe logique.
    2. Pour "MODIFIED", assure-toi de générer le champ 'annotatedDiffV2' avec les balises HTML demandées.
    3. Analyse les contradictions et les lois obsolètes (droit français).
    """

    user_message = f"--- DOCUMENT V1 (Origine) ---\n{text_v1}\n\n--- DOCUMENT V2 (Final) ---\n{text_v2}"

    response = model.generate_content([system_prompt, user_message])
    return json.loads(response.text)

# --- INTERFACE UTILISATEUR ---
st.title("⚖️ Comparateur Légal Intelligent")
st.markdown("Comparez un **Contrat de Réservation (V1)** et un **Acte de Vente (V2)** pour détecter les écarts, ajouts et risques légaux.")

col1, col2 = st.columns(2)
with col1:
    v1_text = st.text_area("Document V1 (Original / Réservation)", height=300, placeholder="Collez le texte du premier contrat ici...")
with col2:
    v2_text = st.text_area("Document V2 (Final / VEFA)", height=300, placeholder="Collez le texte du contrat final ici...")

if st.button("Lancer l'Analyse", type="primary"):
    if not api_key:
        st.error("Veuillez entrer une clé API Gemini dans la barre latérale.")
    elif not v1_text or not v2_text:
        st.warning("Veuillez remplir les deux champs de texte.")
    else:
        with st.spinner("🤖 Analyse par Gemini en cours... (Segmentation, Comparaison, Vérification Légale)"):
            try:
                data = analyze_contracts(v1_text, v2_text, api_key)
                st.session_state['analysis_result'] = data
                st.success("Analyse terminée !")
            except Exception as e:
                st.error(f"Une erreur est survenue : {e}")

# --- AFFICHAGE DES RÉSULTATS ---
if 'analysis_result' in st.session_state:
    data = st.session_state['analysis_result']
    comp_data = data.get("comparisonData", [])
    legal_data = data.get("legalAnalysis", {})

    # Onglets de navigation
    tab1, tab2, tab3 = st.tabs(["📄 Vue Linéaire (Document V2)", "🔍 Vues Groupées", "⚖️ Analyse Légale"])

    # --- VUE 1 : DOCUMENT LINEAIRE ---
    with tab1:
        st.subheader("Reconstitution du Document V2 (Annoté)")
        
        # 1. Afficher le flux V2 (Tout sauf MISSING)
        for item in comp_data:
            if item['category'] == 'MISSING':
                continue # On ne l'affiche pas dans le flux principal
            
            cat_class = f"cat-{item['category']}"
            similarity = f"• Similarité: {item['similarityScore']}%" if item['similarityScore'] else ""
            
            content = item['textV2']
            if item['category'] == 'MODIFIED':
                content = item.get('annotatedDiffV2', item['textV2'])
            
            html_block = f"""
            <div class="report-box {cat_class}">
                <div class="tooltip">{item['category']} {similarity}</div>
                <div>{content}</div>
            </div>
            """
            st.markdown(html_block, unsafe_allow_html=True)

        # 2. Section Récapitulative des MANQUANTS (MISSING)
        missing_items = [i for i in comp_data if i['category'] == 'MISSING']
        if missing_items:
            st.markdown("---")
            st.header("🗑️ Clauses Supprimées (Présentes uniquement en V1)")
            for item in missing_items:
                html_block = f"""
                <div class="report-box cat-MISSING">
                    <div class="tooltip">SUPPRIMÉ DE V2</div>
                    <div>{item['textV1']}</div>
                </div>
                """
                st.markdown(html_block, unsafe_allow_html=True)

    # --- VUE 2 : VUES GROUPÉES ---
    with tab2:
        filter_opt = st.selectbox("Filtrer par catégorie :", ["MODIFIED", "ADDED", "MISSING", "MOVED", "EXACT"])
        
        filtered_items = [i for i in comp_data if i['category'] == filter_opt]
        
        if not filtered_items:
            st.info(f"Aucun paragraphe trouvé pour la catégorie : {filter_opt}")
        
        for item in filtered_items:
            if filter_opt == "MODIFIED":
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**V1 (Original)**")
                    st.info(item['textV1'])
                with c2:
                    st.markdown(f"**V2 (Modifié - {item['similarityScore']}%)**")
                    # Rendu HTML pour voir le gras/barré
                    st.markdown(f"<div class='cat-MODIFIED' style='padding:10px'>{item.get('annotatedDiffV2', item['textV2'])}</div>", unsafe_allow_html=True)
                st.markdown("---")
            else:
                # Affichage simple pour les autres catégories
                st.text_area(f"ID {item['id']}", value=item.get('textV2') or item.get('textV1'), height=100, disabled=True)

    # --- VUE 3 : ANALYSE LÉGALE ---
    with tab3:
        st.header("🛡️ Analyse de Risques & Conformité")
        
        # Lois Obsolètes
        st.subheader("🏛️ Références Légales & Conformité")
        if legal_data.get('obsoleteLaws'):
            for law in legal_data['obsoleteLaws']:
                st.warning(f"**Source : {law['sourceDoc']}**\n\n> \"{law['quote']}\"\n\n**Problème :** {law['issue']}\n\n**Suggestion :** {law['suggestion']}")
        else:
            st.success("Aucune référence légale obsolète détectée.")

        st.divider()

        # Contradictions Internes
        st.subheader("🔄 Contradictions Internes")
        if legal_data.get('internalContradictions'):
            for contra in legal_data['internalContradictions']:
                st.error(f"**Document : {contra['doc']}**\n\nClause concernée : \"{contra['clause']}\"\n\n**Analyse :** {contra['explanation']}")
        else:
            st.success("Aucune contradiction interne flagrante détectée.")
            
        st.divider()

        # Contradictions Inter-Documents
        st.subheader("⚔️ Contradictions entre V1 et V2")
        if legal_data.get('interDocContradictions'):
            for conflict in legal_data['interDocContradictions']:
                st.error(f"**Conflit détecté :**\n\n*V1 dit :* \"{conflict['clauseV1']}\"\n\n*V2 dit :* \"{conflict['clauseV2']}\"\n\n**Description :** {conflict['conflictDescription']}")
        else:
            st.success("Pas de contradiction majeure détectée entre les deux versions.")
