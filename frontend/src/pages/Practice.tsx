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
  const [difficulty,setDifficulty]=useState('intermediate');
  const [classroomSize,setClassroomSize]=useState(4);
  const [session,setSession]=useState<Session|null>(null);
  const [answer,setAnswer]=useState('');
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');

  useEffect(() => {
    let active = true;

    async function loadProjects() {
      try {
        setError('');

        const response = await api.get('/projects');

        const projectList: Project[] = Array.isArray(response.data)
          ? response.data
          : Array.isArray(response.data?.items)
            ? response.data.items
            : Array.isArray(response.data?.projects)
              ? response.data.projects
              : [];

        if (!active) return;

        setProjects(projectList);

        if (projectList.length > 0) {
          setPid(current => current || projectList[0].id);
        } else {
          setError(
            'A API respondeu, mas nenhum treinamento foi encontrado.',
          );
        }
      } catch (err: any) {
        if (!active) return;

        console.error('Erro ao carregar treinamentos:', err);

        setProjects([]);

        const detail = err.response?.data?.detail;

        setError(
          typeof detail === 'string'
            ? detail
            : 'Não foi possível carregar os treinamentos.',
        );
      }
    }

    void loadProjects();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!pid) {
      setSession(null);
      return;
    }

    let active = true;

    async function loadLatestSession() {
      try {
        const response = await api.get(
          `/projects/${pid}/practice/latest`,
        );

        if (active) {
          setSession(response.data || null);
        }
      } catch (err) {
        console.error('Erro ao carregar a última simulação:', err);

        if (active) {
          setSession(null);
        }
      }
    }

    void loadLatestSession();

    return () => {
      active = false;
    };
  }, [pid]);

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
      const nextSession = r.data?.session;

      if (!nextSession) {
        throw new Error(
          'O backend respondeu sem retornar os dados da turma.',
        );
      }

      setSession(nextSession);
      setAnswer('');
    }catch(e:any){
      const detail=e.response?.data?.detail;setError(typeof detail==='string'?detail:`Não foi possível iniciar a turma${e.response?.status?` (erro ${e.response.status})`:''}.`);
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
      const nextSession = r.data?.session;

      if (!nextSession) {
        throw new Error(
          'O backend respondeu sem retornar a continuação da simulação.',
        );
      }

      setSession(nextSession);
      setAnswer('');
    }catch(e:any){
      const detail=e.response?.data?.detail;

      setError(
        typeof detail==='string'
          ? detail
          : e.message||'Não foi possível continuar a simulação.',
      );
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
          {Array.isArray(projects) &&
            projects.map(p=>
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            )
          }
        </select>
      </div>
      <div className="field">
        <label>Dificuldade</label>
        <select
          value={difficulty}
          onChange={e=>setDifficulty(e.target.value)}
        >
          <option value="beginner">iniciante</option>
          <option value="intermediate">intermediário</option>
          <option value="advanced">avançado</option>
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
