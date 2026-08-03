import {
  Check,
  FileText,
  Languages,
  Loader2,
  Pause,
  Play,
  Save,
  Sparkles,
  Square,
  UploadCloud,
  Volume2,
} from 'lucide-react';
import { FormEvent, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import { Glossary, Material, Project, Translation } from '../types';

type InstructorManual = {
  id: number;
  project_id: number;
  material_id: number | null;
  title: string;
  content: string;
  created_at?: string;
  updated_at?: string;
};

export default function Studio() {
  const [sp, setSp] = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [pid, setPid] = useState(Number(sp.get('project') || 0));
  const [materials, setMaterials] = useState<Material[]>([]);
  const [mid, setMid] = useState(0);
  const [current, setCurrent] = useState<Translation | null>(null);
  const [glossary, setGlossary] = useState<Glossary[]>([]);
  const [term, setTerm] = useState({
    source_term: '',
    target_term: '',
    notes: '',
  });
  const [generated, setGenerated] = useState('');
  const [manualId, setManualId] = useState(0);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [speechStatus, setSpeechStatus] = useState<
    'idle' | 'playing' | 'paused'
  >('idle');
  const speechRef = useRef<SpeechSynthesisUtterance | null>(null);
  const speechChunksRef = useRef<string[]>([]);
  const speechChunkIndexRef = useRef(0);
  const speechStoppedRef = useRef(false);

  useEffect(() => {
    api.get('/projects').then((response) => {
      setProjects(response.data);
      if (!pid && response.data[0]) {
        setPid(response.data[0].id);
      }
    });
  }, []);

  useEffect(() => {
    if (!pid) {
      setMaterials([]);
      setGlossary([]);
      setMid(0);
      return;
    }

    setSp({ project: String(pid) });

    const loadProjectData = async () => {
      try {
        const [materialsResponse, glossaryResponse] = await Promise.all([
          api.get(`/projects/${pid}/materials`),
          api.get(`/projects/${pid}/glossary`),
        ]);

        const projectMaterials: Material[] = materialsResponse.data;
        setMaterials(projectMaterials);
        setGlossary(glossaryResponse.data);

        if (projectMaterials.length) {
          const currentStillExists = projectMaterials.some((item) => item.id === mid);
          if (!currentStillExists) {
            setMid(projectMaterials[0].id);
          }
        } else {
          setMid(0);
        }
      } catch (error) {
        console.error('Erro ao carregar dados do projeto:', error);
        setMessage('Não foi possível carregar os dados do treinamento.');
      }
    };

    loadProjectData();
  }, [pid]);

  useEffect(() => {
    if (!mid || !pid) {
      setCurrent(null);
      setGenerated('');
      setManualId(0);
      return;
    }

    const loadMaterialData = async () => {
      try {
        const [translationsResponse, manualsResponse] = await Promise.all([
          api.get(`/materials/${mid}/translations`),
          api.get(`/projects/${pid}/manuals`),
        ]);

        setCurrent(translationsResponse.data[0] || null);

        const savedManual = (manualsResponse.data as InstructorManual[]).find(
          (manual) => manual.material_id === mid,
        );

        if (savedManual) {
          setGenerated(savedManual.content);
          setManualId(savedManual.id);
        } else {
          setGenerated('');
          setManualId(0);
        }
      } catch (error) {
        console.error('Erro ao carregar dados do material:', error);
        setCurrent(null);
        setGenerated('');
        setManualId(0);
        setMessage('Não foi possível carregar tradução e manual deste material.');
      }
    };

    loadMaterialData();
  }, [mid, pid]);


  useEffect(() => {
    const loadVoices = () => {
      window.speechSynthesis.getVoices();
    };

    loadVoices();
    window.speechSynthesis.addEventListener('voiceschanged', loadVoices);

    return () => {
      speechStoppedRef.current = true;
      window.speechSynthesis.cancel();
      window.speechSynthesis.removeEventListener('voiceschanged', loadVoices);
    };
  }, []);

  useEffect(() => {
    speechStoppedRef.current = true;

    if (speechRef.current) {
      speechRef.current.onend = null;
      speechRef.current.onerror = null;
      speechRef.current.onpause = null;
      speechRef.current.onresume = null;
    }

    window.speechSynthesis.cancel();
    speechChunksRef.current = [];
    speechChunkIndexRef.current = 0;
    speechRef.current = null;
    setSpeechStatus('idle');
  }, [mid]);

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem('file') as HTMLInputElement;

    if (!input.files?.[0] || !pid) return;

    setBusy('upload');
    setMessage('');

    try {
      const formData = new FormData();
      formData.append('file', input.files[0]);

      const response = await api.post(`/projects/${pid}/materials`, formData);
      setMaterials((previous) => [response.data, ...previous]);
      setMid(response.data.id);
      input.value = '';
      setMessage('Material enviado e processado com sucesso.');
    } catch (error) {
      console.error('Erro ao enviar material:', error);
      setMessage('Não foi possível enviar o material.');
    } finally {
      setBusy('');
    }
  }

  async function translate() {
    if (!mid) return;

    setBusy('translate');
    setMessage('');

    try {
      const response = await api.post(`/materials/${mid}/translations`, {
        mode: 'didatico',
      });
      setCurrent(response.data);
      setMessage('Tradução gerada com sucesso.');
    } catch (error) {
      console.error('Erro ao gerar tradução:', error);
      setMessage('Não foi possível gerar a tradução.');
    } finally {
      setBusy('');
    }
  }

  async function save() {
    if (!current) return;

    setBusy('save');
    setMessage('');

    try {
      const response = await api.put(`/translations/${current.id}`, {
        translated_text: current.translated_text,
        approved: current.approved,
      });
      setCurrent(response.data);
      setMessage('Revisão salva com sucesso.');
    } catch (error) {
      console.error('Erro ao salvar tradução:', error);
      setMessage('Não foi possível salvar a revisão.');
    } finally {
      setBusy('');
    }
  }

  async function addTerm(event: FormEvent) {
    event.preventDefault();

    if (!pid || !term.source_term || !term.target_term) return;

    setBusy('glossary');
    setMessage('');

    try {
      const response = await api.post(`/projects/${pid}/glossary`, term);
      setGlossary((previous) => [
        ...previous.filter((item) => item.id !== response.data.id),
        response.data,
      ]);
      setTerm({ source_term: '', target_term: '', notes: '' });
      setMessage('Termo salvo no glossário.');
    } catch (error) {
      console.error('Erro ao salvar termo:', error);
      setMessage('Não foi possível salvar o termo.');
    } finally {
      setBusy('');
    }
  }

  async function script() {
    if (!mid || !pid) return;

    setBusy('script');
    setMessage('');

    try {
      const response = await api.post('/generate', {
        project_id: pid,
        material_id: mid,
        kind: 'roteiro',
      });
      setGenerated(response.data.content);
      setManualId(response.data.id || 0);
      setMessage('Manual do instrutor criado e salvo.');
    } catch (error) {
      console.error('Erro ao gerar manual:', error);
      setMessage('Não foi possível criar o manual do instrutor.');
    } finally {
      setBusy('');
    }
  }

  async function saveManual() {
    if (!manualId || !generated.trim()) return;

    setBusy('manual');
    setMessage('');

    try {
      const response = await api.put(`/manuals/${manualId}`, {
        content: generated,
      });
      setGenerated(response.data.content);
      setMessage('Manual salvo com sucesso.');
    } catch (error) {
      console.error('Erro ao salvar manual:', error);
      setMessage('Não foi possível salvar o manual.');
    } finally {
      setBusy('');
    }
  }

  function resolveSpanishLanguage() {
    const project = projects.find((item) => item.id === pid);
    const rawVariant = String(project?.spanish_variant || '').toLowerCase();
    const country = String(project?.country || '').toLowerCase();

    if (rawVariant.includes('ar') || country.includes('argentina')) return 'es-AR';
    if (rawVariant.includes('mx') || country.includes('méxico') || country.includes('mexico')) return 'es-MX';
    if (rawVariant.includes('cl') || country.includes('chile')) return 'es-CL';
    if (rawVariant.includes('co') || country.includes('colombia')) return 'es-CO';
    if (rawVariant.includes('pe') || country.includes('perú') || country.includes('peru')) return 'es-PE';
    if (rawVariant.includes('uy') || country.includes('uruguay')) return 'es-UY';
    if (rawVariant.includes('es') || country.includes('españa') || country.includes('spain')) return 'es-ES';

    return 'es-AR';
  }

  function splitSpeechText(text: string, maxLength = 220) {
    const normalized = text
      .replace(/\*\*/g, '')
      .replace(/^#{1,6}\s+/gm, '')
      .replace(/^[-•]\s+/gm, '')
      .replace(/\n{2,}/g, '. ')
      .replace(/\n/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    const sentences = normalized.match(/[^.!?¿¡]+[.!?¿¡]?/g) || [normalized];
    const chunks: string[] = [];
    let currentChunk = '';

    sentences.forEach((sentence) => {
      const cleanSentence = sentence.trim();
      if (!cleanSentence) return;

      if ((currentChunk + ' ' + cleanSentence).trim().length <= maxLength) {
        currentChunk = `${currentChunk} ${cleanSentence}`.trim();
        return;
      }

      if (currentChunk) {
        chunks.push(currentChunk);
      }

      if (cleanSentence.length <= maxLength) {
        currentChunk = cleanSentence;
        return;
      }

      const words = cleanSentence.split(' ');
      let wordChunk = '';

      words.forEach((word) => {
        if ((wordChunk + ' ' + word).trim().length <= maxLength) {
          wordChunk = `${wordChunk} ${word}`.trim();
        } else {
          if (wordChunk) chunks.push(wordChunk);
          wordChunk = word;
        }
      });

      currentChunk = wordChunk;
    });

    if (currentChunk) {
      chunks.push(currentChunk);
    }

    return chunks;
  }

  function selectSpanishVoice(language: string) {
    const voices = window.speechSynthesis.getVoices();

    return (
      voices.find((voice) => voice.lang.toLowerCase() === language.toLowerCase()) ||
      voices.find((voice) => voice.lang.toLowerCase().startsWith('es-')) ||
      voices.find((voice) => voice.lang.toLowerCase().startsWith('es')) ||
      null
    );
  }

  function playCurrentSpeechChunk() {
    const chunks = speechChunksRef.current;
    const index = speechChunkIndexRef.current;

    if (speechStoppedRef.current || index >= chunks.length) {
      speechRef.current = null;
      setSpeechStatus('idle');
      return;
    }

    const language = resolveSpanishLanguage();
    const utterance = new SpeechSynthesisUtterance(chunks[index]);
    const selectedVoice = selectSpanishVoice(language);

    utterance.lang = selectedVoice?.lang || language;
    utterance.rate = 0.85;
    utterance.pitch = 1;
    utterance.volume = 1;

    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }

    utterance.onstart = () => {
      setSpeechStatus('playing');
    };

    utterance.onpause = () => {
      setSpeechStatus('paused');
    };

    utterance.onresume = () => {
      setSpeechStatus('playing');
    };

    utterance.onend = () => {
      if (speechStoppedRef.current) {
        speechRef.current = null;
        setSpeechStatus('idle');
        return;
      }

      speechChunkIndexRef.current += 1;
      window.setTimeout(playCurrentSpeechChunk, 120);
    };

    utterance.onerror = (event) => {
      const errorCode = String(event.error || '').toLowerCase();

      // O Chrome dispara "interrupted" ou "canceled" quando uma fala
      // anterior é interrompida voluntariamente. Isso não é falha de voz.
      if (
        errorCode === 'interrupted' ||
        errorCode === 'canceled' ||
        speechStoppedRef.current
      ) {
        return;
      }

      console.error('Erro de síntese de voz:', event);
      speechRef.current = null;
      setSpeechStatus('idle');
      setMessage(
        'Não foi possível reproduzir o áudio. Verifique as vozes instaladas no navegador.',
      );
    };

    speechRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  }

  function speak() {
    if (!current?.translated_text) return;

    // Desarma os eventos da fala anterior antes de cancelar.
    if (speechRef.current) {
      speechRef.current.onend = null;
      speechRef.current.onerror = null;
      speechRef.current.onpause = null;
      speechRef.current.onresume = null;
    }

    speechStoppedRef.current = true;
    window.speechSynthesis.cancel();

    speechChunkIndexRef.current = 0;
    speechChunksRef.current = splitSpeechText(current.translated_text);

    if (!speechChunksRef.current.length) {
      setMessage('Não há texto em espanhol disponível para reprodução.');
      setSpeechStatus('idle');
      return;
    }

    setMessage('');
    setSpeechStatus('playing');

    // Pequeno intervalo para o Chrome concluir o cancelamento anterior.
    window.setTimeout(() => {
      speechStoppedRef.current = false;
      playCurrentSpeechChunk();
    }, 180);
  }

  function pauseSpeech() {
    if (!window.speechSynthesis.speaking) return;

    window.speechSynthesis.pause();
    setSpeechStatus('paused');
  }

  function resumeSpeech() {
    if (speechStatus !== 'paused') return;

    window.speechSynthesis.resume();
    setSpeechStatus('playing');

    // Em algumas versões do Chrome, resume() não retoma a fala.
    // Se continuar pausado, reinicia somente o bloco atual.
    window.setTimeout(() => {
      if (!window.speechSynthesis.paused) return;

      if (speechRef.current) {
        speechRef.current.onend = null;
        speechRef.current.onerror = null;
        speechRef.current.onpause = null;
        speechRef.current.onresume = null;
      }

      speechStoppedRef.current = true;
      window.speechSynthesis.cancel();
      speechRef.current = null;

      window.setTimeout(() => {
        speechStoppedRef.current = false;
        setSpeechStatus('playing');
        playCurrentSpeechChunk();
      }, 180);
    }, 300);
  }

  function stopSpeech() {
    speechStoppedRef.current = true;

    if (speechRef.current) {
      speechRef.current.onend = null;
      speechRef.current.onerror = null;
      speechRef.current.onpause = null;
      speechRef.current.onresume = null;
    }

    window.speechSynthesis.cancel();
    speechChunksRef.current = [];
    speechChunkIndexRef.current = 0;
    speechRef.current = null;
    setSpeechStatus('idle');
  }

  const material = materials.find((item) => item.id === mid);

  return (
    <>
      <div className="page-head">
        <div>
          <span className="kicker">CENTRO DE CONTEÚDO</span>
          <h1>Estúdio bilíngue</h1>
          <p>
            Envie, traduza, revise e transforme seus materiais em conteúdo pronto
            para ensinar.
          </p>
        </div>
      </div>

      {message && <div className="panel status-message">{message}</div>}

      <div className="studio-top panel">
        <div className="field">
          <label>Treinamento</label>
          <select value={pid} onChange={(event) => setPid(Number(event.target.value))}>
            <option value={0}>Selecione</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.title} · {project.country}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Material ativo</label>
          <select value={mid} onChange={(event) => setMid(Number(event.target.value))}>
            <option value={0}>Selecione ou envie um arquivo</option>
            {materials.map((item) => (
              <option key={item.id} value={item.id}>
                {item.filename}
              </option>
            ))}
          </select>
        </div>

        <form onSubmit={upload} className="upload-inline">
          <input
            id="material-upload"
            name="file"
            type="file"
            accept=".pdf,.docx,.pptx,.txt,.md"
          />
          <label htmlFor="material-upload">
            <UploadCloud size={19} />
            <span>Selecionar arquivo</span>
          </label>
          <button
            className="btn secondary"
            disabled={!pid || busy === 'upload'}
          >
            {busy === 'upload' ? (
              <Loader2 className="spin" />
            ) : (
              <UploadCloud size={17} />
            )}
            {busy === 'upload' ? 'Enviando...' : 'Enviar'}
          </button>
        </form>
      </div>

      {!mid ? (
        <div className="upload-zone">
          <UploadCloud />
          <h3>Envie o material em português</h3>
          <p>
            PDF, Word, PowerPoint, TXT ou Markdown. O sistema extrairá o conteúdo
            para tradução e estudo.
          </p>
        </div>
      ) : (
        <>
          <div className="studio-actions">
            <button className="btn primary" onClick={translate} disabled={!!busy}>
              <Languages size={18} />
              {busy === 'translate' ? 'Traduzindo...' : 'Gerar tradução didática'}
            </button>

            <button className="btn secondary" onClick={script} disabled={!!busy}>
              <Sparkles size={18} />
              {busy === 'script'
                ? 'Gerando...'
                : manualId
                  ? 'Gerar novo manual'
                  : 'Criar manual do instrutor'}
            </button>

            <div
              className="speech-controls"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                flexWrap: 'wrap',
              }}
            >
              {speechStatus === 'idle' && (
                <button
                  type="button"
                  className="btn ghost"
                  onClick={speak}
                  disabled={!current?.translated_text}
                >
                  <Volume2 size={18} />
                  Ouvir em espanhol
                </button>
              )}

              {speechStatus === 'playing' && (
                <button
                  type="button"
                  className="btn ghost"
                  onClick={pauseSpeech}
                >
                  <Pause size={18} />
                  Pausar
                </button>
              )}

              {speechStatus === 'paused' && (
                <button
                  type="button"
                  className="btn ghost"
                  onClick={resumeSpeech}
                >
                  <Play size={18} />
                  Continuar
                </button>
              )}

              {speechStatus !== 'idle' && (
                <button
                  type="button"
                  className="btn ghost"
                  onClick={stopSpeech}
                >
                  <Square size={17} />
                  Parar
                </button>
              )}
            </div>
          </div>

          <div className="editor-grid">
            <div className="editor-panel">
              <div className="editor-head">
                <div>
                  <span className="lang-badge pt">PT</span>
                  <b>Português original</b>
                </div>
                <small>
                  {(current?.source_text || material?.extracted_text || '').length}{' '}
                  caracteres
                </small>
              </div>
              <textarea
                value={current?.source_text || material?.extracted_text || ''}
                readOnly
              />
            </div>

            <div className="editor-panel">
              <div className="editor-head">
                <div>
                  <span className="lang-badge es">ES</span>
                  <b>Espanhol adaptado</b>
                </div>
                {current?.approved && (
                  <span className="approved">
                    <Check size={15} />
                    Aprovada
                  </span>
                )}
              </div>

              <textarea
                placeholder="A tradução aparecerá aqui..."
                value={current?.translated_text || ''}
                onChange={(event) =>
                  current &&
                  setCurrent({ ...current, translated_text: event.target.value })
                }
              />

              <div className="editor-footer">
                <label className="check-line">
                  <input
                    type="checkbox"
                    checked={current?.approved || false}
                    onChange={(event) =>
                      current &&
                      setCurrent({ ...current, approved: event.target.checked })
                    }
                  />
                  Marcar tradução como aprovada
                </label>

                <button
                  className="btn primary"
                  onClick={save}
                  disabled={!current || !!busy}
                >
                  {busy === 'save' ? (
                    <Loader2 className="spin" size={17} />
                  ) : (
                    <Save size={17} />
                  )}
                  {busy === 'save' ? 'Salvando...' : 'Salvar revisão'}
                </button>
              </div>
            </div>
          </div>

          <div className="studio-bottom">
            <div className="panel glossary-panel">
              <div className="panel-head">
                <div>
                  <span className="label">MEMÓRIA LINGUÍSTICA</span>
                  <h3>Glossário do treinamento</h3>
                </div>
              </div>

              <form className="glossary-form" onSubmit={addTerm}>
                <input
                  placeholder="Termo em português"
                  value={term.source_term}
                  onChange={(event) =>
                    setTerm({ ...term, source_term: event.target.value })
                  }
                />
                <input
                  placeholder="Termo aprovado em espanhol"
                  value={term.target_term}
                  onChange={(event) =>
                    setTerm({ ...term, target_term: event.target.value })
                  }
                />
                <button className="btn secondary" disabled={busy === 'glossary'}>
                  {busy === 'glossary' ? 'Salvando...' : 'Adicionar'}
                </button>
              </form>

              <div className="term-list">
                {glossary.length ? (
                  glossary.map((item) => (
                    <span key={item.id}>
                      {item.source_term}
                      <b>→</b>
                      {item.target_term}
                    </span>
                  ))
                ) : (
                  <p className="muted">Ainda não há termos cadastrados.</p>
                )}
              </div>
            </div>

            <div className="panel material-info">
              <FileText />
              <div>
                <span className="label">MATERIAL ATIVO</span>
                <h3>{material?.filename}</h3>
                <p>Texto extraído e pronto para tradução, roteiro e prática.</p>
              </div>
            </div>
          </div>

          {generated && (
            <div className="panel script-panel">
              <div className="panel-head">
                <div>
                  <span className="label">MANUAL DO INSTRUTOR</span>
                  <h3>Roteiro gerado pela IA</h3>
                </div>
              </div>

              <textarea
                value={generated}
                onChange={(event) => setGenerated(event.target.value)}
              />

              <button
                className="btn primary"
                onClick={saveManual}
                disabled={!manualId || busy === 'manual'}
              >
                {busy === 'manual' ? (
                  <Loader2 className="spin" size={17} />
                ) : (
                  <Save size={17} />
                )}
                {busy === 'manual' ? 'Salvando...' : 'Salvar manual'}
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
}