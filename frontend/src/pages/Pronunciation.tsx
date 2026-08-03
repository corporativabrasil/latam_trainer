import {
  Award,
  Mic,
  RotateCcw,
  Snail,
  Volume2,
  Zap,
} from 'lucide-react';
import {useEffect, useMemo, useState} from 'react';
import {api} from '../services/api';
import {Project} from '../types';

type Result={
  score:number;
  transcript:string;
  missing:string[];
  extra:string[];
  feedback:string;
};

type Attempt={
  score:number;
  transcript:string;
  createdAt:string;
};

const syllables:Record<string,string>={
  buenos:'bue-nos',
  días:'dí-as',
  placer:'pla-cer',
  estar:'es-tar',
  ustedes:'us-te-des',
  liderazgo:'li-de-raz-go',
  producción:'pro-duc-ción',
  comunicación:'co-mu-ni-ca-ción',
  equipo:'e-qui-po',
  fábrica:'fá-bri-ca',
  supervisor:'su-per-vi-sor',
  trabajadores:'tra-ba-ja-do-res',
  organización:'or-ga-ni-za-ción',
  motivación:'mo-ti-va-ción',
  seguridad:'se-gu-ri-dad',
  calidad:'ca-li-dad',
};

function normalize(text:string){
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g,'')
    .replace(/[^a-z0-9ñü\s]/g,'')
    .split(/\s+/)
    .filter(Boolean);
}

function classification(score:number){
  if(score>=96)return {label:'Excelente',symbol:'🏆',message:'Pronúncia com correspondência excelente.'};
  if(score>=85)return {label:'Muito bom',symbol:'🌟',message:'Você está muito próximo da frase esperada.'};
  if(score>=70)return {label:'Bom',symbol:'👍',message:'Bom resultado. Repita as palavras destacadas.'};
  if(score>=50)return {label:'Regular',symbol:'🎯',message:'Repita mais devagar e pratique em blocos.'};
  return {label:'Precisa praticar',symbol:'📚',message:'Escute novamente e pratique palavra por palavra.'};
}

export default function Pronunciation(){
  const [projects,setProjects]=useState<Project[]>([]);
  const [pid,setPid]=useState(0);
  const [phrase,setPhrase]=useState('Buenos días. Es un placer estar con ustedes.');
  const [listening,setListening]=useState(false);
  const [result,setResult]=useState<Result|null>(null);
  const [error,setError]=useState('');
  const [rate,setRate]=useState(.82);
  const [history,setHistory]=useState<Attempt[]>([]);

  useEffect(()=>{
    api.get('/projects').then(r=>{
      setProjects(r.data);
      if(r.data[0])setPid(r.data[0].id);
    });
  },[]);

  useEffect(()=>{
    if(!pid){
      setHistory([]);
      return;
    }
    const stored=localStorage.getItem(`pronunciation-history-${pid}`);
    try{
      setHistory(stored?JSON.parse(stored):[]);
    }catch{
      setHistory([]);
    }
  },[pid]);

  const expectedWords=useMemo(()=>normalize(phrase),[phrase]);
  const transcriptWords=useMemo(()=>normalize(result?.transcript||''),[result]);

  function speakText(text:string,currentRate=rate){
    window.speechSynthesis.cancel();
    const utterance=new SpeechSynthesisUtterance(text);
    utterance.lang='es-419';
    utterance.rate=currentRate;
    utterance.pitch=1;
    utterance.volume=1;
    window.speechSynthesis.speak(utterance);
  }

  function speak(){
    speakText(phrase);
  }

  function saveAttempt(item:Result){
    if(!pid)return;
    const next=[
      ...history,
      {
        score:item.score,
        transcript:item.transcript,
        createdAt:new Date().toISOString(),
      },
    ].slice(-8);
    setHistory(next);
    localStorage.setItem(`pronunciation-history-${pid}`,JSON.stringify(next));
  }

  function record(){
    const SR=(window as any).SpeechRecognition||(window as any).webkitSpeechRecognition;
    if(!SR){
      setError('Seu navegador não oferece reconhecimento de voz. Use Google Chrome ou Microsoft Edge.');
      return;
    }

    window.speechSynthesis.cancel();
    const recognition=new SR();
    recognition.lang='es-419';
    recognition.interimResults=false;
    recognition.continuous=false;
    setListening(true);
    setError('');

    recognition.onresult=async(event:any)=>{
      const transcript=event.results[0][0].transcript;
      try{
        const response=await api.post('/pronunciation/evaluate',{
          project_id:pid,
          expected:phrase,
          transcript,
        });
        setResult(response.data);
        saveAttempt(response.data);
      }catch(err:any){
        setError(err.response?.data?.detail||'Falha ao avaliar a transcrição.');
      }finally{
        setListening(false);
      }
    };

    recognition.onerror=(event:any)=>{
      setListening(false);
      setError(`Falha no microfone: ${event.error}`);
    };
    recognition.onend=()=>setListening(false);
    recognition.start();
  }

  function reset(){
    window.speechSynthesis.cancel();
    setResult(null);
    setError('');
  }

  const level=result?classification(result.score):null;
  const missingSet=new Set((result?.missing||[]).map(normalize).flat());
  const extraSet=new Set((result?.extra||[]).map(normalize).flat());

  return <>
    <div className="page-head">
      <div>
        <span className="kicker">LABORATÓRIO DE VOZ</span>
        <h1>Pronúncia guiada</h1>
        <p>Escute, repita, compare e acompanhe sua evolução em espanhol.</p>
      </div>
    </div>

    <div className="pronunciation-layout">
      <div className="pronunciation-card">
        <div className="field">
          <label>Treinamento</label>
          <select value={pid} onChange={e=>setPid(Number(e.target.value))}>
            <option value={0}>Sem vínculo</option>
            {projects.map(p=><option key={p.id} value={p.id}>{p.title}</option>)}
          </select>
        </div>

        <div className="field">
          <label>Frase para praticar</label>
          <textarea
            value={phrase}
            onChange={e=>{
              setPhrase(e.target.value);
              setResult(null);
            }}
          />
        </div>

        <h2>{phrase}</h2>

        <div
          style={{
            display:'flex',
            justifyContent:'center',
            gap:8,
            marginBottom:16,
            flexWrap:'wrap',
          }}
        >
          <button className={rate===.65?'btn primary':'btn ghost'} onClick={()=>setRate(.65)}>
            <Snail size={16}/> 0,65x
          </button>
          <button className={rate===.82?'btn primary':'btn ghost'} onClick={()=>setRate(.82)}>
            <Volume2 size={16}/> 0,82x
          </button>
          <button className={rate===1?'btn primary':'btn ghost'} onClick={()=>setRate(1)}>
            <Zap size={16}/> 1,0x
          </button>
        </div>

        <div className="audio-controls">
          <button className="round secondary" onClick={speak} title="Ouvir frase">
            <Volume2/>
          </button>
          <button
            className={`record-btn ${listening?'recording':''}`}
            onClick={record}
            disabled={listening}
            title="Gravar"
          >
            <Mic/>
          </button>
          <button className="round secondary" onClick={reset} title="Nova tentativa">
            <RotateCcw/>
          </button>
        </div>

        <div className="record-label">
          {listening?'Ouvindo... fale agora':'Toque no microfone e repita a frase'}
        </div>

        {error&&<p style={{color:'#b42318',fontWeight:700}}>{error}</p>}

        {result&&level&&
          <div style={{marginTop:24}}>
            <div className="score-box">
              <div className="score-circle">
                <strong>{result.score}</strong>
                <span>/100</span>
              </div>
              <div>
                <h3>{level.symbol} {level.label}</h3>
                <p>{level.message}</p>
                <p><b>Transcrição:</b> {result.transcript}</p>
              </div>
            </div>

            <div className="panel" style={{marginTop:16}}>
              <span className="label">FRASE ESPERADA</span>
              <div style={{display:'flex',gap:8,flexWrap:'wrap',marginTop:12}}>
                {expectedWords.map((word,index)=>{
                  const missing=missingSet.has(word);
                  return <button
                    key={`${word}-${index}`}
                    type="button"
                    onClick={()=>speakText(word,.65)}
                    title="Clique para ouvir"
                    style={{
                      border:`1px solid ${missing?'#f4b4b4':'#a8dfd4'}`,
                      background:missing?'#fff2f2':'#eefaf7',
                      color:missing?'#a52222':'#076b5f',
                      borderRadius:999,
                      padding:'8px 12px',
                      cursor:'pointer',
                      fontWeight:700,
                    }}
                  >
                    {missing?'✕':'✓'} {word}
                  </button>;
                })}
              </div>
            </div>

            <div className="panel" style={{marginTop:16}}>
              <span className="label">VOCÊ FALOU</span>
              <div style={{display:'flex',gap:8,flexWrap:'wrap',marginTop:12}}>
                {transcriptWords.map((word,index)=>{
                  const extra=extraSet.has(word);
                  return <span
                    key={`${word}-${index}`}
                    style={{
                      background:extra?'#fff2f2':'#f4f7f7',
                      color:extra?'#a52222':'#264b46',
                      borderRadius:999,
                      padding:'8px 12px',
                      fontWeight:700,
                    }}
                  >
                    {extra?'✕':'•'} {word}
                  </span>;
                })}
              </div>
            </div>

            {(result.missing.length>0||result.extra.length>0)&&
              <div className="panel" style={{marginTop:16}}>
                <span className="label">PRATIQUE NOVAMENTE</span>
                {result.missing.length>0&&<>
                  <h4>Palavras que precisam ser pronunciadas novamente</h4>
                  <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
                    {result.missing.map(word=>
                      <button
                        key={word}
                        type="button"
                        className="btn ghost"
                        onClick={()=>speakText(word,.55)}
                      >
                        <Volume2 size={15}/>
                        {word}
                        {syllables[normalize(word).join('')]&&
                          <small style={{marginLeft:5}}>
                            ({syllables[normalize(word).join('')]})
                          </small>
                        }
                      </button>
                    )}
                  </div>
                </>}
                {result.extra.length>0&&
                  <p><b>Palavras adicionais reconhecidas:</b> {result.extra.join(', ')}</p>
                }
              </div>
            }

            {result.score>=95&&
              <div className="panel" style={{marginTop:16,textAlign:'center'}}>
                <Award size={30}/>
                <h3>{result.score===100?'Pronúncia perfeita':'Excelente pronúncia'}</h3>
                <p>Você demonstrou ótima correspondência com a frase esperada.</p>
              </div>
            }
          </div>
        }
      </div>

      <aside className="practice-sidebar">
        <div className="panel">
          <span className="label">COMO A NOTA É GERADA</span>
          <p>A pontuação compara a frase esperada com a transcrição reconhecida pelo navegador.</p>
          <p>Ela mede correspondência verbal. A avaliação acústica avançada será uma evolução futura.</p>
        </div>

        <div className="panel" style={{marginTop:16}}>
          <span className="label">EVOLUÇÃO</span>
          {!history.length?
            <p>Ainda não há tentativas neste treinamento.</p>
          :
            <div style={{display:'grid',gap:10,marginTop:12}}>
              {history.map((attempt,index)=>
                <div
                  key={`${attempt.createdAt}-${index}`}
                  style={{
                    display:'flex',
                    justifyContent:'space-between',
                    alignItems:'center',
                    borderBottom:'1px solid #e2ece9',
                    paddingBottom:8,
                  }}
                >
                  <span>Tentativa {index+1}</span>
                  <b>{attempt.score}/100</b>
                </div>
              )}
            </div>
          }
        </div>
      </aside>
    </div>
  </>;
}
