import {
  Activity,
  Award,
  BookOpen,
  CheckCircle2,
  Clock3,
  Languages,
  MessageCircleMore,
  Mic2,
  Sparkles,
  Target,
  TrendingUp,
  TriangleAlert,
} from 'lucide-react';
import {useEffect, useMemo, useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {api} from '../services/api';
import {Project} from '../types';

type ActivityItem={
  type:string;
  label:string;
  score:number|null;
  created_at:string|null;
};

type Progress={
  materials:number;
  translations:number;
  approved:number;
  manuals:number;
  simulations:number;
  pronunciation_sessions:number;
  practice_sessions:number;
  average_score:number;
  pronunciation_average:number;
  simulation_average:number;
  readiness:number;
  readiness_label:string;
  components:{
    content:number;
    translation:number;
    manual:number;
    simulation:number;
    pronunciation:number;
  };
  missing_items:string[];
  strengths:string[];
  attention_points:string[];
  recommendations:string[];
  latest_activities:ActivityItem[];
};

function tone(score:number){
  if(score>=90)return '#16a394';
  if(score>=75)return '#2ab8a4';
  if(score>=60)return '#d49a32';
  return '#d45d5d';
}

function readinessText(score:number){
  if(score>=90)return 'Pronto para ministrar';
  if(score>=75)return 'Quase pronto';
  if(score>=60)return 'Em preparação';
  return 'Preparação inicial';
}

function MetricCard({
  icon,
  title,
  value,
  subtitle,
  progress,
}:{
  icon:React.ReactNode;
  title:string;
  value:string;
  subtitle:string;
  progress:number;
}){
  return <div className="panel" style={{padding:22}}>
    <div style={{display:'flex',gap:14,alignItems:'center'}}>
      <div style={{
        width:48,
        height:48,
        display:'grid',
        placeItems:'center',
        borderRadius:14,
        background:'#e8f7f4',
        color:'#08786b',
      }}>
        {icon}
      </div>
      <div>
        <h3 style={{margin:0,fontSize:'1.02rem'}}>{title}</h3>
        <b style={{display:'block',marginTop:4,fontSize:'1.25rem'}}>{value}</b>
        <small style={{color:'#65817c'}}>{subtitle}</small>
      </div>
    </div>
    <div style={{
      height:7,
      background:'#e5efed',
      borderRadius:99,
      marginTop:18,
      overflow:'hidden',
    }}>
      <div style={{
        width:`${Math.max(0,Math.min(100,progress))}%`,
        height:'100%',
        background:tone(progress),
        borderRadius:99,
      }}/>
    </div>
  </div>;
}

export default function Learn(){
  const navigate=useNavigate();
  const [projects,setProjects]=useState<Project[]>([]);
  const [pid,setPid]=useState(0);
  const [progress,setProgress]=useState<Progress|null>(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');

  useEffect(()=>{
    api.get('/projects').then(response=>{
      setProjects(response.data);
      if(response.data[0])setPid(response.data[0].id);
    });
  },[]);

  useEffect(()=>{
    if(!pid){
      setProgress(null);
      return;
    }
    setLoading(true);
    setError('');
    api.get(`/projects/${pid}/progress`)
      .then(response=>setProgress(response.data))
      .catch(error=>setError(error.response?.data?.detail||'Não foi possível calcular a preparação.'))
      .finally(()=>setLoading(false));
  },[pid]);

  const project=projects.find(item=>item.id===pid);
  const readiness=progress?.readiness||0;
  const canTeach=readiness>=90;
  const status=readinessText(readiness);

  const componentRows=useMemo(()=>[
    {label:'Conteúdo processado',value:progress?.components.content||0,weight:'25%'},
    {label:'Tradução aprovada',value:progress?.components.translation||0,weight:'20%'},
    {label:'Manual do instrutor',value:progress?.components.manual||0,weight:'15%'},
    {label:'Simulações IA',value:progress?.components.simulation||0,weight:'25%'},
    {label:'Pronúncia',value:progress?.components.pronunciation||0,weight:'15%'},
  ],[progress]);

  return <>
    <div className="page-head">
      <div>
        <span className="kicker">PRONTIDÃO REAL</span>
        <h1>Preparação do instrutor</h1>
        <p>Seu índice considera conteúdo, tradução, manual, simulações e pronúncia.</p>
      </div>
    </div>

    <div className="panel" style={{padding:22,marginBottom:18}}>
      <div className="field">
        <label>Treinamento</label>
        <select value={pid} onChange={event=>setPid(Number(event.target.value))}>
          <option value={0}>Selecione</option>
          {projects.map(item=><option key={item.id} value={item.id}>{item.title}</option>)}
        </select>
      </div>
    </div>

    {loading&&<div className="panel">Calculando preparação...</div>}
    {error&&<div className="panel">{error}</div>}

    {progress&&<>
      <section
        style={{
          display:'grid',
          gridTemplateColumns:'1fr auto',
          gap:26,
          alignItems:'center',
          padding:'30px 34px',
          borderRadius:20,
          background:'linear-gradient(120deg,#064b45,#0b7568)',
          color:'white',
          marginBottom:20,
          boxShadow:'0 18px 40px rgba(5,73,66,.18)',
        }}
      >
        <div>
          <span style={{
            fontSize:'.72rem',
            letterSpacing:'.16em',
            color:'#81ddd0',
            fontWeight:800,
          }}>
            ÍNDICE DE PRONTIDÃO
          </span>
          <h2 style={{fontSize:'1.65rem',margin:'10px 0 8px'}}>
            {project?.title}
          </h2>
          <p style={{margin:0,color:'#d6f4ef'}}>
            {canTeach
              ? 'Você atingiu o nível recomendado para ministrar este treinamento.'
              : 'Continue avançando nos pontos indicados para elevar sua segurança ao ministrar.'}
          </p>
          <div style={{
            marginTop:18,
            display:'inline-flex',
            alignItems:'center',
            gap:8,
            padding:'8px 12px',
            borderRadius:99,
            background:'rgba(255,255,255,.12)',
            fontWeight:700,
          }}>
            {canTeach?<CheckCircle2 size={18}/>:<Target size={18}/>}
            {status}
          </div>
        </div>

        <div style={{
          width:132,
          height:132,
          borderRadius:'50%',
          display:'grid',
          placeItems:'center',
          background:`conic-gradient(#56d8c5 ${readiness*3.6}deg,rgba(255,255,255,.14) 0deg)`,
          position:'relative',
        }}>
          <div style={{
            width:104,
            height:104,
            borderRadius:'50%',
            background:'#0a665d',
            display:'grid',
            placeItems:'center',
            textAlign:'center',
          }}>
            <div>
              <b style={{fontSize:'2rem'}}>{readiness}%</b>
              <small style={{display:'block',color:'#bfeae3'}}>pronto</small>
            </div>
          </div>
        </div>
      </section>

      <div style={{
        display:'grid',
        gridTemplateColumns:'repeat(2,minmax(0,1fr))',
        gap:18,
        marginBottom:20,
      }}>
        <MetricCard
          icon={<Languages size={23}/>}
          title="Traduções"
          value={`${progress.approved} de ${Math.max(progress.translations,1)}`}
          subtitle="Traduções revisadas e aprovadas"
          progress={progress.components.translation}
        />
        <MetricCard
          icon={<BookOpen size={23}/>}
          title="Conteúdo e manual"
          value={`${progress.materials} material · ${progress.manuals} manual`}
          subtitle="Base de conteúdo disponível para estudo"
          progress={Math.round((progress.components.content+progress.components.manual)/2)}
        />
        <MetricCard
          icon={<MessageCircleMore size={23}/>}
          title="Simulações IA"
          value={`${progress.simulations} realizadas`}
          subtitle={`Média ${progress.simulation_average}/100`}
          progress={progress.components.simulation}
        />
        <MetricCard
          icon={<Mic2 size={23}/>}
          title="Pronúncia"
          value={`${progress.pronunciation_average}/100`}
          subtitle={`${progress.pronunciation_sessions} práticas registradas`}
          progress={progress.components.pronunciation}
        />
      </div>

      <div style={{
        display:'grid',
        gridTemplateColumns:'1.15fr .85fr',
        gap:18,
        marginBottom:20,
      }}>
        <div className="panel" style={{padding:24}}>
          <div className="panel-head">
            <div>
              <span className="label">COMO O ÍNDICE É CALCULADO</span>
              <h3>Componentes da prontidão</h3>
            </div>
          </div>

          <div style={{display:'grid',gap:16}}>
            {componentRows.map(item=><div key={item.label}>
              <div style={{
                display:'flex',
                justifyContent:'space-between',
                gap:12,
                marginBottom:7,
              }}>
                <span>{item.label}</span>
                <span><b>{item.value}%</b> · peso {item.weight}</span>
              </div>
              <div style={{height:8,background:'#e5efed',borderRadius:99,overflow:'hidden'}}>
                <div style={{
                  width:`${item.value}%`,
                  height:'100%',
                  borderRadius:99,
                  background:tone(item.value),
                }}/>
              </div>
            </div>)}
          </div>
        </div>

        <div className="panel" style={{padding:24}}>
          <span className="label">POSSO MINISTRAR ESTE TREINAMENTO?</span>
          <div style={{display:'flex',gap:12,alignItems:'center',margin:'16px 0'}}>
            {canTeach
              ? <Award size={42} color="#118b7d"/>
              : <TriangleAlert size={42} color="#d49a32"/>}
            <div>
              <h3 style={{margin:0}}>{canTeach?'Sim, você está preparado':'Ainda faltam alguns passos'}</h3>
              <p style={{margin:'5px 0 0',color:'#607c77'}}>
                Confiança estimada: <b>{readiness}%</b>
              </p>
            </div>
          </div>

          <p style={{lineHeight:1.65}}>
            {canTeach
              ? 'Seu desempenho já demonstra domínio suficiente para conduzir o treinamento em espanhol. Continue praticando para manter consistência.'
              : 'O sistema recomenda concluir os itens abaixo antes de ministrar este treinamento.'}
          </p>

          <button
            className="btn primary"
            onClick={()=>navigate(canTeach?'/practice':'/pronunciation')}
          >
            <Sparkles size={17}/>
            {canTeach?'Realizar simulação final':'Continuar preparação'}
          </button>
        </div>
      </div>

      <div style={{
        display:'grid',
        gridTemplateColumns:'repeat(3,minmax(0,1fr))',
        gap:18,
        marginBottom:20,
      }}>
        <div className="panel" style={{padding:22}}>
          <span className="label">PONTOS FORTES</span>
          <div style={{display:'grid',gap:10,marginTop:14}}>
            {(progress.strengths.length?progress.strengths:['Continue praticando para consolidar pontos fortes.'])
              .map(item=><div key={item} style={{display:'flex',gap:9}}>
                <CheckCircle2 size={18} color="#118b7d"/>
                <span>{item}</span>
              </div>)}
          </div>
        </div>

        <div className="panel" style={{padding:22}}>
          <span className="label">PRECISA MELHORAR</span>
          <div style={{display:'grid',gap:10,marginTop:14}}>
            {(progress.attention_points.length?progress.attention_points:['Nenhum ponto crítico identificado.'])
              .map(item=><div key={item} style={{display:'flex',gap:9}}>
                <Target size={18} color="#d49a32"/>
                <span>{item}</span>
              </div>)}
          </div>
        </div>

        <div className="panel" style={{padding:22}}>
          <span className="label">FALTA CONCLUIR</span>
          <div style={{display:'grid',gap:10,marginTop:14}}>
            {(progress.missing_items.length?progress.missing_items:['Todos os critérios principais foram concluídos.'])
              .map(item=><div key={item} style={{display:'flex',gap:9}}>
                <Activity size={18} color={progress.missing_items.length?'#d45d5d':'#118b7d'}/>
                <span>{item}</span>
              </div>)}
          </div>
        </div>
      </div>

      <div style={{
        display:'grid',
        gridTemplateColumns:'1fr 1fr',
        gap:18,
      }}>
        <div className="panel" style={{padding:24}}>
          <div className="panel-head">
            <div>
              <span className="label">COPILOTO RECOMENDA</span>
              <h3>Próximas ações</h3>
            </div>
            <Sparkles color="#118b7d"/>
          </div>

          <div style={{display:'grid',gap:12}}>
            {progress.recommendations.map((item,index)=>
              <div key={item} style={{
                display:'grid',
                gridTemplateColumns:'34px 1fr',
                alignItems:'start',
                gap:10,
              }}>
                <div style={{
                  width:30,
                  height:30,
                  display:'grid',
                  placeItems:'center',
                  borderRadius:'50%',
                  background:'#e8f7f4',
                  color:'#08786b',
                  fontWeight:800,
                }}>
                  {index+1}
                </div>
                <span style={{lineHeight:1.55}}>{item}</span>
              </div>
            )}
          </div>
        </div>

        <div className="panel" style={{padding:24}}>
          <div className="panel-head">
            <div>
              <span className="label">ATIVIDADES RECENTES</span>
              <h3>Histórico de preparação</h3>
            </div>
            <Clock3 color="#118b7d"/>
          </div>

          <div style={{display:'grid',gap:12}}>
            {!progress.latest_activities.length&&
              <p style={{color:'#66817d'}}>Ainda não há atividades registradas.</p>}
            {progress.latest_activities.map((item,index)=>
              <div key={`${item.type}-${index}`} style={{
                display:'flex',
                justifyContent:'space-between',
                alignItems:'center',
                gap:12,
                paddingBottom:10,
                borderBottom:'1px solid #e6efed',
              }}>
                <div>
                  <b>{item.label}</b>
                  <small style={{display:'block',marginTop:4,color:'#6a8580'}}>
                    {item.created_at
                      ? new Date(item.created_at).toLocaleString('pt-BR')
                      : 'Data não disponível'}
                  </small>
                </div>
                {item.score!==null&&<b>{item.score}/100</b>}
              </div>
            )}
          </div>
        </div>
      </div>

      {canTeach&&
        <div className="panel" style={{
          marginTop:20,
          padding:28,
          textAlign:'center',
          background:'#f0fbf8',
          border:'1px solid #bfe9df',
        }}>
          <Award size={44} color="#118b7d"/>
          <h2 style={{margin:'12px 0 6px'}}>Instrutor preparado</h2>
          <p style={{margin:0}}>
            Você atingiu o nível recomendado para ministrar <b>{project?.title}</b> em espanhol.
          </p>
        </div>
      }
    </>;
}
