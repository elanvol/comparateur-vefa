import React, { useState, useEffect } from 'react';
import { AlertCircle, FileText, ArrowRight, CheckCircle, Settings, Upload, RefreshCw, Shield, Move, MinusCircle, PlusCircle, Edit3 } from 'lucide-react';

// --- CONFIGURATION ---
// This component handles the entire logic locally.
// We rely on the user providing an API Key.

const App = () => {
  const [apiKey, setApiKey] = useState('');
  const [textV1, setTextV1] = useState('');
  const [textV2, setTextV2] = useState('');
  const [status, setStatus] = useState('idle'); // idle, loading, success, error
  const [errorMsg, setErrorMsg] = useState('');
  const [result, setResult] = useState(null);
  const [viewMode, setViewMode] = useState('document'); // 'document' or 'grouped'
  const [dragActive, setDragActive] = useState(false);

  // --- GEMINI INTEGRATION ---
  const analyzeContracts = async () => {
    if (!apiKey) {
      setErrorMsg("Veuillez entrer une clé API Gemini valide.");
      return;
    }
    if (!textV1.trim() || !textV2.trim()) {
      setErrorMsg("Veuillez fournir le contenu des deux contrats.");
      return;
    }

    setStatus('loading');
    setErrorMsg('');

    const systemPrompt = `
      You are a legal contract comparison engine. Your task is to compare "Contract V1" (Reservation) against "Contract V2" (Final VEFA).
      
      Analyze the texts paragraph by paragraph. Return ONLY a valid JSON array of objects. No markdown formatting, no preamble.
      
      Each object in the array represents a segment of the final document (V2) OR a missing segment from V1.
      Structure each object exactly like this:
      {
        "type": "unchanged" | "modified" | "moved" | "removed" | "added",
        "content": "The text content of the paragraph",
        "original_content": "Original text from V1 if modified or removed, else null",
        "similarity": number (0-100),
        "diff_html": "For type 'modified' ONLY: An HTML string where deleted words are wrapped in <del class='text-red-600 bg-red-100 strike-through decoration-2'> and added words in <strong class='text-red-600'>. Otherwise null.",
        "original_position": "For type 'moved': description of original location (e.g., 'Moved from Section 1'), else null"
      }

      Rules for classification:
      - unchanged: Exact match or negligible whitespace difference.
      - modified: Content is largely similar but has specific word changes/numbers changed.
      - moved: The paragraph exists in V1 but is in a significantly different location in V2.
      - removed: A paragraph present in V1 but completely missing in V2.
      - added: A paragraph present in V2 that has no equivalent in V1.
    `;

    const userPrompt = `
      --- CONTRACT V1 (ORIGINAL) ---
      ${textV1}
      
      --- CONTRACT V2 (FINAL) ---
      ${textV2}
    `;

    try {
      const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{
            role: "user",
            parts: [{ text: systemPrompt + "\n" + userPrompt }]
          }],
          generationConfig: {
            responseMimeType: "application/json"
          }
        })
      });

      if (!response.ok) throw new Error("Erreur lors de l'appel API. Vérifiez votre clé.");

      const data = await response.json();
      const generatedText = data.candidates[0].content.parts[0].text;
      const jsonResult = JSON.parse(generatedText);
      
      setResult(jsonResult);
      setStatus('success');

    } catch (err) {
      console.error(err);
      setStatus('error');
      setErrorMsg(err.message || "Une erreur est survenue lors de l'analyse.");
    }
  };

  // --- UI HELPERS ---
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const getBgColor = (type) => {
    switch (type) {
      case 'unchanged': return 'bg-green-50 border-green-200';
      case 'modified': return 'bg-yellow-50 border-yellow-200';
      case 'moved': return 'bg-blue-50 border-blue-200';
      case 'removed': return 'bg-gray-100 border-gray-300 opacity-75';
      case 'added': return 'bg-red-50 border-red-200';
      default: return 'bg-white';
    }
  };

  const getIcon = (type) => {
    switch (type) {
      case 'unchanged': return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'modified': return <Edit3 className="w-5 h-5 text-yellow-600" />;
      case 'moved': return <Move className="w-5 h-5 text-blue-600" />;
      case 'removed': return <MinusCircle className="w-5 h-5 text-gray-600" />;
      case 'added': return <PlusCircle className="w-5 h-5 text-red-600" />;
      default: return null;
    }
  };

  const getLabel = (type) => {
    switch (type) {
      case 'unchanged': return 'Repris à l\'identique';
      case 'modified': return 'Clause Modifiée';
      case 'moved': return 'Déplacé';
      case 'removed': return 'Manquant dans V2';
      case 'added': return 'Ajout dans V2';
      default: return type;
    }
  };

  // --- DEMO DATA LOADING ---
  const loadDemoData = () => {
    setTextV1(`ARTICLE 3 - PRIX
Le prix de vente est fixé à 250.000 euros.
Ce prix est ferme et définitif.
Le dépôt de garantie est de 5%.

ARTICLE 4 - DÉLAI
La livraison est prévue au 1er trimestre 2024.
En cas de retard, une pénalité de 10€ par jour sera due.`);

    setTextV2(`ARTICLE 3 - PRIX DE VENTE
Le prix de vente est fixé à 255.000 euros.
Ce prix est ferme, définitif et non révisable.

ARTICLE 4 - DÉLAI DE LIVRAISON
La livraison est prévue au 2ème trimestre 2024.
Le dépôt de garantie est ramené à 2%.
(Clause ajoutée sur la force majeure excluant les pénalités)`);
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800">
      {/* HEADER */}
      <header className="bg-white shadow-sm border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-2 rounded-lg text-white">
              <FileText size={24} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900">ContractMatch AI</h1>
              <p className="text-xs text-slate-500">Comparateur VEFA intelligent</p>
            </div>
          </div>

          <div className="flex items-center gap-2 bg-slate-100 p-2 rounded-md border border-slate-200 w-full md:w-auto">
            <Settings size={16} className="text-slate-400" />
            <input 
              type="password" 
              placeholder="Votre Clé API Gemini"
              className="bg-transparent border-none outline-none text-sm w-full md:w-64"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
          </div>
        </div>
      </header>

      {/* MAIN CONTENT */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        
        {/* INPUT SECTION (Shown if no result yet) */}
        {status === 'idle' && (
          <div className="space-y-6 animate-fade-in">
            <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg text-sm text-blue-800 flex items-start gap-3">
              <AlertCircle className="shrink-0 mt-0.5" size={18} />
              <p>
                Pour analyser vos contrats, collez le texte brut ci-dessous. 
                <strong>Note :</strong> Dans cette version démo, l'upload de fichiers PDF nécessite une conversion manuelle en texte.
                <button onClick={loadDemoData} className="underline ml-2 font-semibold hover:text-blue-900">Charger un exemple de démo</button>
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-[500px]">
              {/* V1 INPUT */}
              <div className="flex flex-col gap-2 h-full">
                <label className="font-semibold text-slate-700 flex items-center gap-2">
                  <span className="bg-slate-200 text-slate-600 px-2 py-0.5 rounded text-xs">Original</span>
                  Contrat Réservation (V1)
                </label>
                <textarea 
                  className="flex-1 w-full p-4 border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none font-mono text-sm"
                  placeholder="Collez le texte du contrat de réservation ici..."
                  value={textV1}
                  onChange={(e) => setTextV1(e.target.value)}
                />
              </div>

              {/* V2 INPUT */}
              <div className="flex flex-col gap-2 h-full">
                <label className="font-semibold text-slate-700 flex items-center gap-2">
                  <span className="bg-slate-200 text-slate-600 px-2 py-0.5 rounded text-xs">Final</span>
                  Contrat VEFA (V2)
                </label>
                <textarea 
                  className="flex-1 w-full p-4 border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none font-mono text-sm"
                  placeholder="Collez le texte du contrat final ici..."
                  value={textV2}
                  onChange={(e) => setTextV2(e.target.value)}
                />
              </div>
            </div>

            <div className="flex justify-center pt-4">
              <button 
                onClick={analyzeContracts}
                disabled={!textV1 || !textV2}
                className="bg-slate-900 hover:bg-slate-800 text-white px-8 py-3 rounded-full font-bold shadow-lg flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Lancer l'analyse comparative <ArrowRight size={18} />
              </button>
            </div>
          </div>
        )}

        {/* LOADING STATE */}
        {status === 'loading' && (
          <div className="flex flex-col items-center justify-center py-20 space-y-4">
            <RefreshCw className="animate-spin text-blue-600" size={48} />
            <div className="text-center">
              <h3 className="text-xl font-semibold">Analyse juridique en cours...</h3>
              <p className="text-slate-500">Gemini compare chaque clause et détecte les anomalies.</p>
            </div>
          </div>
        )}

        {/* ERROR STATE */}
        {status === 'error' && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-md mb-6">
            <div className="flex items-center gap-3">
              <AlertCircle className="text-red-600" />
              <h3 className="font-bold text-red-700">Erreur d'analyse</h3>
            </div>
            <p className="text-red-600 mt-1">{errorMsg}</p>
            <button 
              onClick={() => setStatus('idle')}
              className="mt-4 text-sm font-semibold text-red-700 underline"
            >
              Réessayer
            </button>
          </div>
        )}

        {/* RESULTS VIEW */}
        {status === 'success' && result && (
          <div className="animate-fade-in-up">
            {/* Toolbar */}
            <div className="flex flex-col sm:flex-row justify-between items-center mb-6 gap-4">
              <div className="flex bg-white p-1 rounded-lg border border-slate-200 shadow-sm">
                <button 
                  onClick={() => setViewMode('document')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${viewMode === 'document' ? 'bg-blue-100 text-blue-700' : 'text-slate-600 hover:bg-slate-50'}`}
                >
                  Vue Documentaire
                </button>
                <button 
                  onClick={() => setViewMode('grouped')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${viewMode === 'grouped' ? 'bg-blue-100 text-blue-700' : 'text-slate-600 hover:bg-slate-50'}`}
                >
                  Vues Groupées
                </button>
              </div>
              <button onClick={() => setStatus('idle')} className="text-sm text-slate-500 hover:text-slate-800 flex items-center gap-1">
                <RefreshCw size={14} /> Nouvelle analyse
              </button>
            </div>

            {/* VIEW: LINEAR DOCUMENT */}
            {viewMode === 'document' && (
              <div className="bg-white shadow-xl rounded-xl overflow-hidden border border-slate-200">
                 <div className="bg-slate-50 px-6 py-3 border-b border-slate-200 flex items-center justify-between">
                    <h2 className="font-bold text-slate-700">Contrat VEFA (Annoté)</h2>
                    <div className="flex gap-3 text-xs">
                      <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-green-200"></span> Identique</span>
                      <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-yellow-200"></span> Modifié</span>
                      <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-red-200"></span> Ajout</span>
                    </div>
                 </div>
                 <div className="p-8 space-y-4 max-w-4xl mx-auto">
                    {result.map((item, idx) => (
                      <div 
                        key={idx} 
                        className={`relative group p-4 rounded-lg border transition-all duration-200 ${getBgColor(item.type)}`}
                      >
                        {/* Floating Badge */}
                        <div className="absolute -top-3 left-4 px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-white border border-slate-200 shadow-sm flex items-center gap-1">
                           {getIcon(item.type)} {getLabel(item.type)}
                           {item.similarity > 0 && item.type === 'modified' && (
                             <span className="text-slate-400 ml-1">| {item.similarity}% sim.</span>
                           )}
                        </div>

                        {/* Content */}
                        <div className="mt-2 text-slate-800 leading-relaxed">
                          {item.type === 'modified' && item.diff_html ? (
                            <div dangerouslySetInnerHTML={{ __html: item.diff_html }} />
                          ) : (
                             item.content
                          )}
                        </div>

                        {/* Tooltip / Details for Modified/Moved */}
                        {(item.type === 'modified' || item.type === 'moved') && (
                          <div className="mt-3 pt-3 border-t border-black/5 text-sm text-slate-600 hidden group-hover:block animate-fade-in">
                            {item.original_content && (
                               <div className="mb-1">
                                 <span className="font-semibold text-slate-900">Original (V1) :</span> {item.original_content}
                               </div>
                            )}
                            {item.original_position && (
                               <div className="text-blue-700 italic">
                                 📍 {item.original_position}
                               </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                 </div>
              </div>
            )}

            {/* VIEW: GROUPED CATEGORIES */}
            {viewMode === 'grouped' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {['modified', 'added', 'removed', 'moved', 'unchanged'].map(category => {
                  const items = result.filter(r => r.type === category);
                  if (items.length === 0) return null;

                  return (
                    <div key={category} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full">
                      <div className={`px-4 py-3 border-b font-bold flex items-center justify-between ${
                        category === 'modified' ? 'bg-yellow-50 text-yellow-800' :
                        category === 'added' ? 'bg-red-50 text-red-800' :
                        category === 'removed' ? 'bg-gray-100 text-gray-800' :
                        category === 'moved' ? 'bg-blue-50 text-blue-800' :
                        'bg-green-50 text-green-800'
                      }`}>
                        <span className="flex items-center gap-2">{getIcon(category)} {getLabel(category)}</span>
                        <span className="bg-white/50 px-2 rounded text-sm">{items.length}</span>
                      </div>
                      <div className="p-4 space-y-3 overflow-y-auto max-h-[600px]">
                        {items.map((item, idx) => (
                          <div key={idx} className="text-sm bg-slate-50 p-3 rounded border border-slate-100">
                            {category === 'modified' ? (
                                <div dangerouslySetInnerHTML={{ __html: item.diff_html || item.content }} />
                            ) : (
                                <div>{item.content}</div>
                            )}
                            {item.original_content && category === 'modified' && (
                              <div className="mt-2 text-xs text-slate-500 pt-2 border-t border-slate-200">
                                <strong>Avant :</strong> {item.original_content}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
