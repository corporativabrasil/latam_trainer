import {
  BarChart3,
  BookOpen,
  Languages,
  LogOut,
  Menu,
  MessageCircleMore,
  Mic2,
  PanelLeftClose,
  PanelLeftOpen,
  PenLine,
  Sparkles,
  X,
} from 'lucide-react';
import {useEffect, useState} from 'react';
import {NavLink, Outlet, useLocation, useNavigate} from 'react-router-dom';

const links=[
  ['/', 'Visão geral', BarChart3],
  ['/projects', 'Treinamentos', BookOpen],
  ['/studio', 'Estúdio bilíngue', Languages],
  ['/learn', 'Plano de preparação', Sparkles],
  ['/practice', 'Simulador IA', MessageCircleMore],
  ['/pronunciation', 'Pronúncia', Mic2],
  ['/spanish-lab', 'Laboratório de espanhol', PenLine],
] as const;

export default function Layout(){
  const navigate=useNavigate();
  const location=useLocation();
  const [collapsed,setCollapsed]=useState(false);
  const [mobileOpen,setMobileOpen]=useState(false);

  useEffect(()=>{
    setMobileOpen(false);
  },[location.pathname]);

  useEffect(()=>{
    document.body.classList.toggle('mobile-nav-open',mobileOpen);

    const closeOnEscape=(event:KeyboardEvent)=>{
      if(event.key==='Escape')setMobileOpen(false);
    };

    window.addEventListener('keydown',closeOnEscape);
    return ()=>{
      document.body.classList.remove('mobile-nav-open');
      window.removeEventListener('keydown',closeOnEscape);
    };
  },[mobileOpen]);

  function logout(){
    localStorage.removeItem('token');
    setMobileOpen(false);
    navigate('/login');
  }

  return (
    <div className={`app-shell ${collapsed?'collapsed':''}`}>
      <button
        type="button"
        className={`mobile-overlay ${mobileOpen?'visible':''}`}
        aria-label="Fechar menu"
        onClick={()=>setMobileOpen(false)}
      />

      <aside className={`sidebar ${mobileOpen?'mobile-open':''}`}>
        <div className="brand-wrap">
          <div className="brand-mark">CB</div>
          <div className="brand-copy">
            <strong>Corporativa</strong>
            <span>LATAM Trainer AI</span>
          </div>
          <button
            type="button"
            className="mobile-close"
            aria-label="Fechar menu"
            onClick={()=>setMobileOpen(false)}
          >
            <X size={21}/>
          </button>
        </div>

        <button
          type="button"
          className="collapse-btn"
          aria-label={collapsed?'Expandir menu':'Recolher menu'}
          onClick={()=>setCollapsed(!collapsed)}
        >
          {collapsed?<PanelLeftOpen size={19}/>:<PanelLeftClose size={19}/>}
        </button>

        <nav>
          {links.map(([to,label,Icon])=>
            <NavLink
              key={to}
              to={to}
              end={to==='/'}
              title={label}
              onClick={()=>setMobileOpen(false)}
            >
              <Icon size={20}/>
              <span>{label}</span>
            </NavLink>
          )}
        </nav>

        <div className="sidebar-bottom">
          <div className="ai-badge">
            <Sparkles size={18}/>
            <div>
              <b>Copiloto ativo</b>
              <small>Preparação em espanhol</small>
            </div>
          </div>
          <button className="logout" onClick={logout}>
            <LogOut size={19}/>
            <span>Sair</span>
          </button>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="mobile-menu"
              aria-label="Abrir menu"
              aria-expanded={mobileOpen}
              onClick={()=>setMobileOpen(true)}
            >
              <Menu size={22}/>
            </button>
            <span className="eyebrow">AMBIENTE DE PREPARAÇÃO DO INSTRUTOR</span>
          </div>

          <div className="top-user">
            <div className="status-dot"/>
            <div>
              <b>Prof. Márcio Silva</b>
              <small>Instrutor</small>
            </div>
            <div className="avatar">MS</div>
          </div>
        </header>

        <section className="content">
          <Outlet/>
        </section>
      </main>
    </div>
  );
}
