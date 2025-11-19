import streamlit as st
from docx import Document
from docx.shared import RGBColor, Pt
from docx.enum.text import WD_COLOR_INDEX
import difflib
import re
from io import BytesIO
import google.generativeai as genai
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="Assistant Comparaison IA", page_icon="⚖️", layout="wide")

# --- FONCTIONS UTILITAIRES ---

def configure_gemini(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')

def get_cleaned_paragraphs(doc):
    """Extrait les paragraphes non vides avec leur index d'origine"""
    return [{'text': p.text.strip(), 'obj': p, 'matched': False} 
            for p in doc.paragraphs if p.text.strip() != '']

def ask_gemini_annotation(model, text_B, text_A_candidate, is_candidate_found):
    """
    Interroge l'IA pour obtenir l'annotation précise selon les règles de l'utilisateur.
    """
    
    # Si aucun candidat n'a été trouvé par l'algo de recherche, c'est un ajout
    if not is_candidate_found:
        return "[Ajouté]"

    prompt = f"""
    Tu es un assistant spécialisé en comparaison de documents.
    Compare le passage B (document à analyser) avec le passage A (document de référence).

    PASSAGE A (Reference) : "{text_A_candidate}"
    PASSAGE B (A analyser) : "{text_B}"

    Ta mission : Retourne UNIQUEMENT l'annotation correspondante parmi ces choix :
    1. Si identique (ou différences mineures de ponctuation/casse) -> "[Repris tel quel]"
    2. Si le sens est le même mais formulé différemment ou changements de valeurs -> "[Modifié : explication courte de la différence]"
    3. Si c'est clairement le même paragraphe mais à un endroit différent -> "[Déplacé depuis A]"
    
    Ne mets pas de guillemets autour de ta réponse. Réponds juste le tag.
    """
    
    try:
        # Température 0 pour des réponses factuelles et strictes
        response = model.generate_content(prompt, generation_config={"temperature": 0.0})
        return response.text.strip()
    except Exception:
        return "[Erreur Analyse IA]"

def style_run(run, color_rgb, bold=True):
    run.font.color.rgb = color_rgb
    run.font.bold = bold
    run.font.size = Pt(9) # Un peu plus petit pour l'annotation

# --- MOTEUR PRINCIPAL ---

def generate_comparison_report(file_ref, file_target, model):
    doc_ref = Document(file_ref)
    doc_target = Document(file_target) # C'est le Texte B qui sera annoté
    
    # 1. Indexation du Document A (Référence)
    ref_paras = get_cleaned_paragraphs(doc_ref)
    
    # 2. Itération sur le Document B (Cible)
    total_paras_target = len([p for p in doc_target.paragraphs if p.text.strip() != ''])
    current_idx = 0
    progress_bar = st.progress(0)
    status_text = st.empty()

    for p_target in doc_target.paragraphs:
        text_B = p_target.text.strip()
        if not text_B:
            continue
        
        current_idx += 1
        status_text.text(f"Analyse du passage {current_idx}/{total_paras_target}...")
        progress_bar.progress(current_idx / total_paras_target)

        # --- Etape A : Recherche du meilleur candidat dans A (Algorithme rapide) ---
        best_match_idx = -1
        best_ratio = 0.0
        
        for idx, p_ref in enumerate(ref_paras):
            # On utilise difflib pour trouver le paragraphe de A qui ressemble le plus à B
            ratio = difflib.SequenceMatcher(None, p_ref['text'], text_B).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match_idx = idx
        
        # --- Etape B : Décision IA ---
        
        annotation = ""
        color = RGBColor(0, 0, 0) # Noir par défaut
        
        # Seuil de détection (si < 0.4, on considère que ça n'existe pas dans A)
        candidate_found = best_ratio > 0.4 
        text_candidate = ref_paras[best_match_idx]['text'] if candidate_found else ""

        # Appel IA
        if candidate_found:
            # Si c'est quasi identique (gain de temps/tokens), on force la réponse
            if best_ratio > 0.98:
                annotation = "[Repris tel quel]"
            else:
                # Sinon l'IA décide si c'est Modifié ou Déplacé
                annotation = ask_gemini_annotation(model, text_B, text_candidate, True)
            
            # On marque le paragraphe de A comme "Utilisé"
            ref_paras[best_match_idx]['matched'] = True
            
        else:
            annotation = "[Ajouté]"

        # --- Etape C : Insertion de l'annotation dans le Doc B ---
        
        # Choix des couleurs pour la lisibilité
        if "[Repris tel quel]" in annotation:
            color = RGBColor(34, 139, 34) # Forest Green
        elif "[Modifié" in annotation:
            color = RGBColor(255, 140, 0) # Dark Orange
        elif "[Déplacé" in annotation:
            color = RGBColor(30, 144, 255) # Dodger Blue
        elif "[Ajouté]" in annotation:
            color = RGBColor(220, 20, 60) # Crimson Red
        
        # Ajout de l'annotation à la fin du paragraphe
        run = p_target.add_run(" " + annotation)
        style_run(run, color)

    # 3. Création du Tableau des Oubliés (Fin du document)
    doc_target.add_page_break()
    heading = doc_target.add_heading('TABLEAU DES ÉLÉMENTS MANQUANTS (OUBLIÉS DANS B)', level=1)
    heading.style.font.color.rgb = RGBColor(255, 0, 0)
    
    # Création du tableau
    table = doc_target.add_table(rows=1, cols=2)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Statut'
    hdr_cells[1].text = 'Passage du Texte A (Référence) absent de B'
    
    count_forgotten = 0
    for p_ref in ref_paras:
        if not p_ref['matched']:
            count_forgotten += 1
            row_cells = table.add_row().cells
            
            # Colonne Statut
            run_statut = row_cells[0].paragraphs[0].add_run("[Oublié dans B]")
            run_statut.font.color.rgb = RGBColor(255, 0, 0)
            run_statut.font.bold = True
            
            # Colonne Texte
            row_cells[1].text = p_ref['text']

    return doc_target, count_forgotten

# --- INTERFACE UTILISATEUR ---

st.title("⚖️ Assistant Comparaison de Documents (IA)")
st.markdown("""
Cet outil compare **Texte A** et **Texte B** et génère un rapport Word annoté selon vos règles :
- `[Repris tel quel]` (Vert)
- `[Modifié : ...]` (Orange)
- `[Ajouté]` (Rouge)
- `[Oublié dans B]` (Tableau final)
""")

with st.sidebar:
    st.header("🔑 Configuration")
    api_key = st.text_input("Clé API Gemini", type="password", help="Nécessaire pour l'analyse sémantique.")
    st.info("L'analyse peut prendre quelques minutes selon la taille des fichiers.")

col1, col2 = st.columns(2)
with col1:
    file_A = st.file_uploader("Texte A (Référence)", type=["docx"])
with col2:
    file_B = st.file_uploader("Texte B (À annoter)", type=["docx"])

if file_A and file_B and api_key:
    if st.button("Générer le Rapport de Comparaison"):
        model = configure_gemini(api_key)
        
        with st.spinner("Comparaison IA en cours..."):
            try:
                # Exécution
                result_doc, missing_count = generate_comparison_report(file_A, file_B, model)
                
                # Préparation téléchargement
                output = BytesIO()
                result_doc.save(output)
                output.seek(0)
                
                st.success(f"Terminé ! {missing_count} passages du texte A ont été oubliés dans le texte B.")
                
                st.download_button(
                    label="📥 Télécharger le Rapport Annoté (.docx)",
                    data=output,
                    file_name="Rapport_Comparaison_IA.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
            except Exception as e:
                st.error(f"Une erreur est survenue : {e}")
elif not api_key and (file_A or file_B):
    st.warning("Veuillez entrer votre clé API Gemini pour lancer l'IA.")
