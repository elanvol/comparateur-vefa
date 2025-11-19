import streamlit as st
from docx import Document
import difflib
import re

st.set_page_config(page_title="Document Comparison Pro", page_icon="📄", layout="wide")

def read_docx(file):
    """Extrait le texte d'un fichier .docx"""
    doc = Document(file)
    return ' '.join([para.text for para in doc.paragraphs])

def compare_documents(text1, text2):
    """Compare deux textes et retourne les différences"""
    words1 = text1.split()
    words2 = text2.split()
    
    differ = difflib.Differ()
    diff = list(differ.compare(words1, words2))
    
    insertions = [w[2:] for w in diff if w.startswith('+ ')]
    deletions = [w[2:] for w in diff if w.startswith('- ')]
    
    return {
        'diff': diff,
        'insertions': len(insertions),
        'deletions': len(deletions)
    }

# Interface
st.title("📄 Document Comparison Pro")
st.markdown("Comparez deux documents Word et visualisez leurs différences")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📁 Document Original")
    file1 = st.file_uploader("Choisir le fichier", type=['docx', 'txt'], key="file1")

with col2:
    st.subheader("📁 Document Modifié")
    file2 = st.file_uploader("Choisir le fichier", type=['docx', 'txt'], key="file2")

if file1 and file2:
    if st.button("🔍 Comparer les documents", type="primary"):
        with st.spinner("Analyse en cours..."):
            # Lecture des fichiers
            text1 = read_docx(file1) if file1.name.endswith('.docx') else file1.read().decode()
            text2 = read_docx(file2) if file2.name.endswith('.docx') else file2.read().decode()
            
            # Comparaison
            results = compare_documents(text1, text2)
            
            # Statistiques
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            col_stat1.metric("✅ Ajouts", results['insertions'])
            col_stat2.metric("❌ Suppressions", results['deletions'])
            col_stat3.metric("📊 Total modifications", results['insertions'] + results['deletions'])
            
            # Résultats
            st.subheader("📝 Résultat de la comparaison")
            result_html = ""
            for item in results['diff']:
                if item.startswith('+ '):
                    result_html += f'<span style="background-color: #d4edda; color: #155724; padding: 2px 4px; border-radius: 3px; text-decoration: underline;">{item[2:]}</span> '
                elif item.startswith('- '):
                    result_html += f'<span style="background-color: #f8d7da; color: #721c24; padding: 2px 4px; border-radius: 3px; text-decoration: line-through;">{item[2:]}</span> '
                elif item.startswith('  '):
                    result_html += f'{item[2:]} '
            
            st.markdown(result_html, unsafe_allow_html=True)
