import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type Task = { id:number; title:string; due_date:string|null; completed:boolean }
type Deadline = { id:number; label:string; kind:'official'|'personal'; due_date:string|null; due_time:string|null; timezone:string|null }
type Application = { id:number; title:string; provider:string|null; source_url:string|null; cycle:string|null; status:string; notes:string|null; next_action:string|null; archived:boolean; submission_date:string|null; interview_date:string|null; outcome:string|null; tasks:Task[]; deadlines:Deadline[] }
type Draft = Omit<Application,'id'|'tasks'|'deadlines'>
const empty:Draft = {title:'',provider:'',source_url:'',cycle:'',status:'researching',notes:'',next_action:'',archived:false,submission_date:null,interview_date:null,outcome:''}
const statuses = ['researching','preparing','submitted','result_received','withdrawn']
const label = (s:string) => s.replaceAll('_',' ').replace(/^./, c=>c.toUpperCase())
async function api<T>(url:string, method='GET', body?:unknown):Promise<T> {
  const r=await fetch(url,{method,headers:method==='GET'?{}:{'Content-Type':'application/json','X-Requested-With':'ScholarshipTracker'},body:body===undefined?undefined:JSON.stringify(body)})
  if(!r.ok){ const d=await r.json().catch(()=>({})); const detail=d.detail; throw new Error(typeof detail==='string'?detail:detail?.message || `Request failed (${r.status})`) }
  return r.json() as Promise<T>
}
export default function App(){
  const [items,setItems]=useState<Application[]>([]), [archived,setArchived]=useState(false), [search,setSearch]=useState(''), [status,setStatus]=useState('')
  const [editing,setEditing]=useState<number|null>(null), [draft,setDraft]=useState<Draft|null>(null), [error,setError]=useState(''), [busy,setBusy]=useState(false)
  const [task,setTask]=useState(''), [deadline,setDeadline]=useState(''), [deadlineDate,setDeadlineDate]=useState(''), [kind,setKind]=useState<'official'|'personal'>('official')
  async function load(){try{const params=new URLSearchParams({archived:String(archived),q:search,status});setItems(await api<Application[]>(`/api/applications?${params}`));setError('')}catch(e){setError(e instanceof Error?e.message:'Could not load applications')}}
  useEffect(()=>{
    let active=true
    const params=new URLSearchParams({archived:String(archived),q:search,status})
    api<Application[]>(`/api/applications?${params}`).then(rows=>{if(active){setItems(rows);setError('')}}).catch(e=>{if(active)setError(e instanceof Error?e.message:'Could not load applications')})
    return ()=>{active=false}
  },[archived,search,status])
  const selected=items.find(x=>x.id===editing)
  function edit(item:Application){const {id,tasks,deadlines,...rest}=item; void id; void tasks; void deadlines;setDraft(rest);setEditing(item.id);setError('')}
  function change<K extends keyof Draft>(key:K,value:Draft[K]){setDraft(d=>d?{...d,[key]:value}:d)}
  async function save(e:FormEvent){e.preventDefault();if(!draft)return;setBusy(true);try{const body={...draft,provider:draft.provider||null,source_url:draft.source_url||null,cycle:draft.cycle||null,notes:draft.notes||null,next_action:draft.next_action||null,outcome:draft.outcome||null};const row=await api<Application>(editing===null?'/api/applications':`/api/applications/${editing}`,editing===null?'POST':'PUT',body);setEditing(row.id);await load()}catch(e){setError(e instanceof Error?e.message:'Could not save')}finally{setBusy(false)}}
  async function updateArchive(item:Application){try{const {id,tasks,deadlines,...data}=item;void tasks;void deadlines;await api(`/api/applications/${id}`,'PUT',{...data,archived:!item.archived});setDraft(null);setEditing(null);await load()}catch(e){setError(e instanceof Error?e.message:'Could not update')}}
  async function addTask(e:FormEvent){e.preventDefault();if(!editing||!task.trim())return;try{await api(`/api/applications/${editing}/tasks`,'POST',{title:task.trim(),due_date:null,completed:false});setTask('');await load()}catch(e){setError(e instanceof Error?e.message:'Could not add task')}}
  async function saveTask(t:Task,changes:Partial<Task>){if(!editing)return;try{await api(`/api/applications/${editing}/tasks/${t.id}`,'PUT',{...t,...changes});await load()}catch(e){setError(e instanceof Error?e.message:'Could not update task')}}
  async function removeTask(t:Task){if(!editing)return;try{await api(`/api/applications/${editing}/tasks/${t.id}`,'DELETE');await load()}catch(e){setError(e instanceof Error?e.message:'Could not remove task')}}
  async function addDeadline(e:FormEvent){e.preventDefault();if(!editing||!deadline.trim())return;try{await api(`/api/applications/${editing}/deadlines`,'POST',{label:deadline.trim(),kind,due_date:deadlineDate||null,due_time:null,timezone:null});setDeadline('');setDeadlineDate('');await load()}catch(e){setError(e instanceof Error?e.message:'Could not add deadline')}}
  async function removeDeadline(d:Deadline){if(!editing)return;try{await api(`/api/applications/${editing}/deadlines/${d.id}`,'DELETE');await load()}catch(e){setError(e instanceof Error?e.message:'Could not remove deadline')}}
  async function saveDeadline(d:Deadline,changes:Partial<Deadline>){if(!editing)return;try{await api(`/api/applications/${editing}/deadlines/${d.id}`,'PUT',{...d,...changes});await load()}catch(e){setError(e instanceof Error?e.message:'Could not update deadline')}}
  return <main className="app-shell"><header><span className="brand">Scholarship Tracker</span><span className="local-label">Your private workspace</span></header>
    <section className="workspace-heading"><div><p className="eyebrow">YOUR APPLICATION WORKSPACE</p><h1>My Applications</h1><p>Keep your opportunities, deadlines and next steps together.</p></div><button className="primary" onClick={()=>{setEditing(null);setDraft({...empty});setError('')}}>Add manually</button></section>
    {error && <div className="alert" role="alert">{error}</div>}
    <div className="toolbar"><input aria-label="Search applications" placeholder="Search applications" value={search} onChange={e=>setSearch(e.target.value)}/><select aria-label="Filter by status" value={status} onChange={e=>setStatus(e.target.value)}><option value="">All statuses</option>{statuses.map(s=><option key={s} value={s}>{label(s)}</option>)}</select><label><input type="checkbox" checked={archived} onChange={e=>{setArchived(e.target.checked);setDraft(null);setEditing(null)}}/> Show archived</label></div>
    <div className="layout"><section aria-label="Applications">{items.length===0?<div className="empty-state"><h2>No applications yet</h2><p>Add an application to start tracking it.</p></div>:items.map(item=><article className="card" key={item.id}><div className="card-head"><h2>{item.title}</h2><span className="badge">{label(item.status)}</span></div><p>{item.provider||'Provider not recorded'}{item.cycle?` · ${item.cycle}`:''}</p><p><strong>Next deadline:</strong> {item.deadlines.find(d=>d.due_date)?.due_date||'Not recorded'}</p><p><strong>Next action:</strong> {item.next_action||'Not recorded'}</p><div className="actions"><button onClick={()=>edit(item)}>Open application</button><button onClick={()=>void updateArchive(item)}>{item.archived?'Restore':'Archive'}</button></div></article>)}</section>
    {draft && <section className="editor"><div className="card-head"><h2>{editing===null?'Add application':'Application details'}</h2><button onClick={()=>{setDraft(null);setEditing(null)}}>Close</button></div><form onSubmit={save}>
      <label>Scholarship name<input required maxLength={250} value={draft.title} onChange={e=>change('title',e.target.value)}/></label>
      <label>Provider<input value={draft.provider||''} onChange={e=>change('provider',e.target.value)}/></label>
      <label>Announcement URL<input type="url" value={draft.source_url||''} onChange={e=>change('source_url',e.target.value)}/></label>
      <label>Cycle<input value={draft.cycle||''} placeholder="For example, 2027–2028" onChange={e=>change('cycle',e.target.value)}/></label>
      <label>Progress<select value={draft.status} onChange={e=>change('status',e.target.value)}>{statuses.map(s=><option key={s} value={s}>{label(s)}</option>)}</select></label>
      <label>Next action<textarea value={draft.next_action||''} onChange={e=>change('next_action',e.target.value)}/></label>
      <label>Personal notes<textarea value={draft.notes||''} onChange={e=>change('notes',e.target.value)}/></label>
      <label>Submission date<input type="date" value={draft.submission_date||''} onChange={e=>change('submission_date',e.target.value||null)}/></label>
      <label>Interview date<input type="date" value={draft.interview_date||''} onChange={e=>change('interview_date',e.target.value||null)}/></label>
      <label>Outcome<input value={draft.outcome||''} placeholder="For example, accepted" onChange={e=>change('outcome',e.target.value)}/></label>
      <button className="primary" disabled={busy} type="submit">Save application</button></form>
      {selected && <><h3>Deadlines</h3>{selected.deadlines.map(d=><div className="list-row" key={d.id}><input aria-label="Edit deadline name" defaultValue={d.label} onBlur={e=>{if(e.target.value.trim()&&e.target.value!==d.label)void saveDeadline(d,{label:e.target.value})}}/><span>{label(d.kind)}</span><input aria-label="Edit deadline date" type="date" value={d.due_date||''} onChange={e=>void saveDeadline(d,{due_date:e.target.value||null})}/><button onClick={()=>void removeDeadline(d)}>Remove</button></div>)}<form className="inline-form" onSubmit={addDeadline}><input aria-label="Deadline name" placeholder="Deadline name" value={deadline} onChange={e=>setDeadline(e.target.value)}/><select aria-label="Deadline type" value={kind} onChange={e=>setKind(e.target.value as 'official'|'personal')}><option value="official">Official</option><option value="personal">Personal</option></select><input aria-label="Deadline date" type="date" value={deadlineDate} onChange={e=>setDeadlineDate(e.target.value)}/><button type="submit">Add deadline</button></form>
      <h3>Tasks</h3>{selected.tasks.map(t=><div className="list-row" key={t.id}><label><input type="checkbox" checked={t.completed} onChange={e=>void saveTask(t,{completed:e.target.checked})}/><input aria-label="Task title" defaultValue={t.title} onBlur={e=>{if(e.target.value.trim()&&e.target.value!==t.title)void saveTask(t,{title:e.target.value})}}/></label><button onClick={()=>void removeTask(t)}>Remove</button></div>)}<form className="inline-form" onSubmit={addTask}><input aria-label="New task" placeholder="Add a task" value={task} onChange={e=>setTask(e.target.value)}/><button type="submit">Add task</button></form></>}
    </section>}</div></main>
}
