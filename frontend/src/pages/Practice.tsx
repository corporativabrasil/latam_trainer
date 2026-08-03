import {
  Bot,
  Send,
  Sparkles,
  StopCircle,
  UserRound,
  UsersRound,
} from 'lucide-react';
import {useEffect, useState} from 'react';
import {api} from '../services/api';
import {Project} from '../types';

type Participant={
  id:number;
  name:string;
  role:string;
  personality:string;
  behavior:string;
  expertise_level:string;
  emotion:string;
  avatar_code:string;
};

type Message={
  id:number;
  role:string;
  content:string;
  message_type:string;
  metadata:Record<string,any>;
};

type Session={
  id:number;
  project_id:number;
  difficulty:string;
  status:string;
  overall:number;
  scores:Record<string,number>;
  messages:Message[];
  participants:Participant[];
};

export default function Practice(){
  const [projects,setProjects]=useState<Project[]>([]);
  const [pid,setPid]=useState(0);
  const [difficulty,setDifficulty]=useState('intermediário');
  const [classroomSize,setClassroomSize]=useState(4);
  const [session,setSession]=useState<Session|null>(null);
  const [answer,setAnswer]=useState('');
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');

  useEffect(()=>{
    api.get('/projects').then(r=>{
      setProjects(r.data);
      if(r.data[0])setPid(r.data[0].id);
    });
  },[]);

  useEffect(()=>{
    if(!pid)return;
    api.get(`/projects/${pid}/practice/latest`)
      .then(r=>setSession(r.data||null))
      .catch(()=>setSession(null));
  },[pid]);

  async function start(){
    setLoading(true);setError('');
    try{
      const r=await api.post('/simulation',{
        project_id:pid,
        difficulty,
        classroom_size:classroomSize,
        user_answer:'',
        session_id:null,
        action:'continue',
      });
      setSession(r.data.session);
      setAnswer('');
    }catch(e:any){
      setError(e.response?.data?.detail||'Não foi possível iniciar a turma.');
    }finally{setLoading(false)}
  }

  async function send(action:'continue'|'finish'){
    if(!session||!answer.trim())return;
    setLoading(true);setError('');
    try{
      const r=await api.post('/simulation',{
        project_id:pid,
        difficulty,
        classroom_size:classroomSize,
        user_answer:answer,
        session_id:session.id,
        action,
      });
      setSession(r.data.session);
      setAnswer('');
    }catch(e:any){
      setError(e.response?.data?.detail||'Não foi possível continuar a simulação.');
    }finally{setLoading(false)}
  }

  const participants = session?.participants ?? [];
  const visibleMessages = (session?.messages ?? []).filter(
    m => m.message_type !== 'hidden_evaluation',
  );

  return <>
    <div className="page-head">
      <div>
        <span className="kicker">SIMULADOR IA 2.0</span>
        <h1>Sala de treinamento virtual</h1>
        <p>Pratique com uma turma que pergunta, discorda e reage como participantes reais.</p>
      </div>
    </div>

    <div className="sim-config panel">
      <div className="field">
        <label>Treinamento</label>
        <select value={pid} onChange={e=>setPid(Number(e.target.value))}>
          <option value={0}>Selecione</option>
          {projects.map(p=><option key={p.id} value={p.id}>{p.title}</option>)}
        </select>
      </div>
      <div className="field">
        <label>Dificuldade</label>
        <select value={difficulty} onChange={e=>setDifficulty(e.target.value)}>
          <option>iniciante</option><option>intermediário</option><option>avançado</option>
        </select>
      </div>
      <div className="field">
        <label>Participantes</label>
        <select value={classroomSize} onChange={e=>setClassroomSize(Number(e.target.value))}>
          {[1,2,3,4,5,6,7,8].map(n=><option key={n} value={n}>{n}</option>)}
        </select>
      </div>
      <button className="btn primary" onClick={start} disabled={!pid||loading}>
        <UsersRound size={18}/>{loading?'Preparando...':'Nova turma'}
      </button>
    </div>

    {error&&<div className="panel" style={{marginBottom:16}}>{error}</div>}

    {participants.length > 0 &&
      <div className="panel" style={{marginBottom:16}}>
        <div className="panel-head">
          <div><span className="label">SUA TURMA</span><h3>Participantes virtuais</h3></div>
        </div>
        <div className="term-list">
          {participants.map(p=>
            <span key={p.id} title={`${p.personality} · ${p.emotion}`}>
              <b>{p.avatar_code}</b> {p.name} · {p.role}
            </span>
          )}
        </div>
      </div>
    }

    <div className="chat-shell">
      <div className="chat-head">
        <div className="participant-avatar"><UsersRound/></div>
        <div>
          <b>{session?.status==='finished'?'Simulação concluída':'Turma industrial'}</b>
          <small>{session?.status==='active'?'Avaliação ocorrendo em segundo plano':'Pronto para iniciar'}</small>
        </div>
      </div>

      <div className="chat-body">
        {!visibleMessages.length?
          <div className="chat-empty"><Bot/><h3>Crie sua turma</h3><p>A IA usará os slides, a tradução, o manual e o país.</p></div>
        :
          visibleMessages.map(m=>{
            if(m.role==='instructor')return <div className="message instructor" key={m.id}>
              <div>{m.content}</div><div className="mini-avatar">MS</div>
            </div>;

            if(m.message_type==='final_report'){
              const data=m.metadata||{};
              return <div className="feedback-box" key={m.id}>
                <Sparkles/><div>
                  <b>Relatório final · {data.overall||session?.overall||0}/100</b>
                  <p>{data.coach_summary||m.content}</p>
                  <div className="term-list">
                    {Object.entries(data.scores||{}).map(([k,v])=><span key={k}>{k}: <b>{String(v)}</b></span>)}
                  </div>
                  <h4>Pontos fortes</h4><p>{(data.strengths||[]).join(' · ')}</p>
                  <h4>Pontos a melhorar</h4><p>{(data.improvements||[]).join(' · ')}</p>
                  <h4>Plano de estudo</h4><p>{Array.isArray(data.study_plan)?data.study_plan.join(' · '):data.study_plan}</p>
                </div>
              </div>;
            }

            const speaker=m.metadata?.speaker_name||'Participante';
            const emotion=m.metadata?.emotion;
            const participant=participants.find(p=>p.name===speaker);
            return <div className="message participant" key={m.id}>
              <div className="mini-avatar">
                {participant?.avatar_code||<UserRound size={16}/>}
              </div>
              <div>
                <b style={{display:'block',marginBottom:5}}>
                  {speaker}
                  {emotion&&
                    <small style={{marginLeft:8,fontWeight:500,opacity:.7}}>
                      {emotion}
                    </small>
                  }
                </b>
                {m.content}
              </div>
            </div>;
          })
        }
      </div>

      {session?.status==='active'&&
        <div className="chat-input">
          <textarea placeholder="Responda em espanhol..." value={answer} onChange={e=>setAnswer(e.target.value)}/>
          <button className="send-btn" title="Responder" disabled={loading||!answer.trim()} onClick={()=>send('continue')}><Send/></button>
          <button className="send-btn" title="Responder e encerrar" disabled={loading||!answer.trim()} onClick={()=>send('finish')} style={{marginLeft:8}}><StopCircle/></button>
        </div>
      }
    </div>
  </>;
}
