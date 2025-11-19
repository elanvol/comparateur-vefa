import streamlit as st
from docx import Document
from docx.shared import RGBColor
from docx.enum.text import WD_COLOR_INDEX
import difflib
import re
from io import BytesIO
import google.generativeai as genai

# --- CONFIGURATION GEMINI ---
def configure_gemini(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')

# --- FONCTIONS UTILITAIRES ---

def normalize_text_simple(text):
    """Normalisation basique pour la pré-vérification"""
    text = text.strip()
    # Substitution simple pour éviter d'appeler l'IA si c'est juste un changement de mot-clé évident
    text = re.sub(r'\bRESERVANT\b', 'VENDEUR', text, flags=re.IGNORECASE)
    text = re.sub(r'\bRESERVATAIRE\b', 'ACQUEREUR', text, flags=re.IGNORECASE)
    return text

def ask_gemini_analysis(model, text_source, text_target):
    """
    Envoie les deux textes à Gemini pour une comparaison intelligente.
    """
    prompt = f"""
    Agis comme un juriste expert en immobilier. Compare ces deux clauses.
    
    CONTEXTE :
    - Texte 1 : Contrat de Réservation (RÉSERVANT / RÉSERVATAIRE)
    - Texte 2 : Contrat VEFA (VENDEUR / ACQUÉREUR)
    - Ignore le changement de nom des parties (Réservant=Vendeur, Réservataire=Acquéreur).

    TEXTE 1 (ORIGINE) : "{text_source}"
    TEXTE 2 (FINAL) : "{text_target}"

    TACHE :
    Analyse les différences. Réponds UNIQUEMENT au format suivant :
    STATUT: [IDENTIQUE | MODIFIE_MINEUR | MODIFIE_MAJEUR | INCOHERENCE]
    COMMENTAIRE: [Ton explication courte en 1 phrase. Si INCOHERENCE, précise les chiffres/dates qui changent]
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"STATUT: ERREUR\nCOMMENTAIRE: Erreur API ({str(e)})"

def parse_gemini_response(response_text):
    """Extrait le statut et le commentaire de la réponse brute de Gemini"""
    statut = "INCONNU"
    commentaire = ""
    
    lines = response_text.split('\n')
    for line in lines:
        if line.startswith("STATUT:"):
            statut = line.replace("STATUT:", "").strip()
        if line.startswith("COMMENTAIRE:"):
            commentaire = line.replace("COMMENTAIRE:", "").strip()
            
    return statut, commentaire

def apply_color(paragraph, color_rgb):
    """Applique une couleur à tout le paragraphe."""
    for run in paragraph.runs:
        run.font.color.rgb = color_rgb

def add_comment(paragraph, text, highlight_color):
    """Simule un commentaire en ajoutant du texte surligné à la fin du paragraphe"""
    run = paragraph.add_run(f" [{text}]")
    run.font.highlight_color = highlight_color
    run.font.bold = True
    # On essaie de garder la taille de police du paragraphe s'il y en a une définie
    if paragraph.runs and paragraph.runs[0].font.size:
        run.font.size = paragraph.runs[0].font.size

def compare_documents_with_ai(file_resa, file_vefa, model):
    doc_resa = Document(file_resa)
    doc_vefa = Document(file_vefa)
    
    # Extraction
    resa_paragraphs = [{'text': p.text, 'matched': False} for p in doc_resa.paragraphs if p.text.strip() != '']
    
    progress_bar = st.progress(0)
    total_paras = len(doc_vefa.paragraphs)
    
    for i, p_vefa in enumerate(doc_vefa.paragraphs):
        # Mise à jour barre de progression (gestion des divisions par zéro si doc vide)
        if total_paras > 0:
            progress_bar.progress((i + 1) / total_paras)
        
        text_vefa = p_vefa.text.strip()
        if not text_vefa:
            continue
            
        best_match_index = -1
        best_ratio = 0
        
        # 1. Recherche algorithmique rapide
        for idx, p_resa in enumerate(resa_paragraphs):
            if p_resa['matched']: continue
            
            ratio = difflib.SequenceMatcher(None, normalize_text_simple(p_resa['text']), text_vefa).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match_index = idx
        
        # SEUILS DE DECISION
        if best_ratio > 0.98:
            apply_color(p_vefa, RGBColor(0, 128, 0))
            resa_paragraphs[best_match_index]['matched'] = True
            
        elif best_ratio > 0.60:
            text_source = resa_paragraphs[best_match_index]['text']
            
            ai_raw_response = ask_gemini_analysis(model, text_source, text_vefa)
            statut, commentaire = parse_gemini_response(ai_raw_response)
            
            resa_paragraphs[best_match_index]['matched'] = True
            
            if "IDENTIQUE" in statut or "MODIFIE_MINEUR" in statut:
                apply_color(p_vefa, RGBColor(0, 128, 0)) 
                if "MODIFIE_MINEUR" in statut:
                    add_comment(p_vefa, f"IA: {commentaire}", WD_COLOR_INDEX.BRIGHT_GREEN)
                    
            elif "INCOHERENCE" in statut:
                apply_color(p_vefa, RGBColor(255, 0, 0)) 
                add_comment(p_vefa, f"⚠️ ALERTE IA : {commentaire}", WD_COLOR_INDEX.YELLOW)
                
            else: 
                apply_color(p_vefa, RGBColor(255, 165, 0)) 
                add_comment(p_vefa, f"Modification : {commentaire}", WD_COLOR_INDEX.TURQUOISE)

        else:
            apply_color(p_vefa, RGBColor(255, 0, 0))
            add_comment(p_vefa, "Ajout : Clause absente du contrat de réservation", WD_COLOR_INDEX.PINK)

    # --- CORRECTION DE L'ERREUR ICI ---
    doc_vefa.add_page_break()
    doc_vefa.add_heading('ANNEXE : CLAUSES NON REPRISES (DÉTECTÉES PAR IA)', level=1)
    
    count_forgotten = 0
    for p_resa in resa_paragraphs:
        if not p_resa['matched']:
            count_forgotten += 1
            # On crée le paragraphe vide
            p = doc_vefa.add_paragraph()
            # On ajoute un "run" (le texte) pour pouvoir le styliser
            run = p.add_run(p_resa['text'])
            run.font.italic = True
            run.font.color.rgb = RGBColor(128, 128, 128) # Gris

    return doc_vefa, count_forgotten

# --- INTERFACE ---

st.set_page_config(page_title="Immo-Check AI", page_icon="🤖")

st.title("🤖 Comparateur Juridique Intelligent (via Gemini)")
st.markdown("Cette version utilise **Google Gemini** pour comprendre le sens des phrases et détecter les incohérences (prix, dates) même si le texte est reformulé.")

with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Entrez votre Clé API Gemini", type="password", help="Obtenez-la sur aistudio.google.com")
    st.warning("Sans clé API, l'application ne fonctionnera pas.")

col1, col2 = st.columns(2)
with col1:
    file_resa = st.file_uploader("Contrat Réservation", type=["docx"])
with col2:
    file_vefa = st.file_uploader("Contrat VEFA", type=["docx"])

if file_resa and file_vefa and api_key:
    if st.button("Lancer l'Analyse IA"):
        model = configure_gemini(api_key)
        with st.spinner('L\'IA lit et compare les contrats... Cela peut prendre un peu de temps.'):
            try:
                result_doc, missing = compare_documents_with_ai(file_resa, file_vefa, model)
                
                output = BytesIO()
                result_doc.save(output)
                output.seek(0)
                
                st.success("Analyse IA terminée !")
                st.download_button("Télécharger le rapport annoté", data=output, file_name="Rapport_VEFA_IA.docx")
            except Exception as e:
                st.error(f"Erreur : {e}")
elif not api_key and (file_resa or file_vefa):
    st.info("Veuillez entrer une clé API dans la barre latérale pour activer l'intelligence artificielle.")
