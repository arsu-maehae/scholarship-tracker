// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import App from './App'
import type { DashboardTask } from './dashboard'

const emptyExtraction={latest:null,previous_found:null,official_pages:[],page_attempts:[]}

describe('attention dashboard and dated tasks',()=>{
  let rows: Array<{id:number;source_url:string;title:string|null;provider:string|null;intake:string|null;deadline:string|null;funding:string|null;eligibility:string|null;notes:string|null;status:string;archived_at:string|null;checklist:DashboardTask[]}>=[
    {id:1,source_url:'https://example.org/alpha',title:'Alpha',provider:'Example University',intake:null,deadline:'2026-11-25',funding:null,eligibility:null,notes:null,status:'preparing',archived_at:null,checklist:[
      {id:11,label:'Submit passport',completed:false,due_date:'2026-11-26'},
      {id:12,label:'Ask referee',completed:false,due_date:'2026-12-10'},
      {id:13,label:'Late boundary',completed:false,due_date:'2026-12-11'},
      {id:14,label:'Completed task',completed:true,due_date:'2026-11-25'},
    ]},
    {id:2,source_url:'https://example.org/beta',title:'Beta',provider:null,intake:null,deadline:'2026-11-26',funding:null,eligibility:null,notes:null,status:'saved',archived_at:null,checklist:[]},
    {id:3,source_url:'https://example.org/gamma',title:'Gamma',provider:null,intake:null,deadline:null,funding:null,eligibility:null,notes:null,status:'submitted',archived_at:null,checklist:[{id:31,label:'Done',completed:true,due_date:null}]},
  ]
  const taskPatches:unknown[]=[]
  const taskCreates:unknown[]=[]

  beforeEach(()=>{
    vi.useFakeTimers({toFake:['Date']})
    vi.setSystemTime(new Date('2026-11-25T17:30:00Z'))
    taskPatches.length=0;taskCreates.length=0
    rows=structuredClone(rows)
    vi.stubGlobal('fetch',vi.fn(async(input:RequestInfo|URL,init?:RequestInit)=>{
      const path=String(input)
      if(path.includes('/api/tracked-scholarships?'))return new Response(JSON.stringify(rows),{status:200})
      if(path.endsWith('/1/extraction'))return new Response(JSON.stringify(emptyExtraction),{status:200})
      if(path.endsWith('/1')&&(!init?.method||init.method==='GET'))return new Response(JSON.stringify(rows[0]),{status:200})
      if(path.endsWith('/1/checklist/11')&&init?.method==='PATCH'){
        const body=JSON.parse(String(init.body));taskPatches.push(body);rows[0].checklist[0]={...rows[0].checklist[0],...body}
        return new Response(JSON.stringify(rows[0].checklist[0]),{status:200})
      }
      if(path.endsWith('/1/checklist')&&init?.method==='POST'){
        const body=JSON.parse(String(init.body));taskCreates.push(body);rows[0].checklist.push({id:99,...body})
        return new Response(JSON.stringify(rows[0].checklist.at(-1)),{status:201})
      }
      throw new Error(`Unexpected request: ${init?.method||'GET'} ${path}`)
    }))
  })

  afterEach(()=>{cleanup();vi.useRealTimers();vi.unstubAllGlobals()})

  it('shows deadline groups, unknown dates, progress, and only tasks needing attention',async()=>{
    render(<App/>)
    expect(await screen.findByRole('heading',{name:'Overdue confirmed deadlines'})).toBeTruthy()
    expect(screen.getByRole('heading',{name:'Upcoming confirmed deadlines'})).toBeTruthy()
    expect(screen.getByText('Wed, 25 Nov 2026')).toBeTruthy()
    expect(screen.getByText('Thu, 26 Nov 2026')).toBeTruthy()
    expect(screen.getByText('Submit passport')).toBeTruthy()
    expect(screen.getByText('Ask referee')).toBeTruthy()
    expect(screen.queryByText('Late boundary')).toBeNull()
    expect(screen.queryByText('Completed task')).toBeNull()
    expect(screen.getByText('Date not confirmed')).toBeTruthy()
    expect(screen.getByText('1/4 tasks complete')).toBeTruthy()
    expect(screen.getByText('1/1 tasks complete')).toBeTruthy()
    expect(screen.getAllByText('Preparing')).not.toHaveLength(0)
  })

  it('updates and persists task dates and creates a dated task',async()=>{
    render(<App/>)
    const saved=await screen.findByRole('region',{name:'Saved scholarships'})
    const alphaCard=within(saved).getByRole('heading',{name:'Alpha'}).closest('article') as HTMLElement
    fireEvent.click(within(alphaCard).getByRole('button',{name:'Open'}))
    const date=await screen.findByLabelText('Due date for Submit passport')
    fireEvent.change(date,{target:{value:'2026-11-28'}})
    await waitFor(()=>expect(taskPatches).toContainEqual({due_date:'2026-11-28'}))
    await waitFor(()=>expect((screen.getByLabelText('Due date for Submit passport') as HTMLInputElement).value).toBe('2026-11-28'))

    fireEvent.change(screen.getByPlaceholderText('Add a task'),{target:{value:'Upload transcript'}})
    fireEvent.change(screen.getByLabelText('New task due date'),{target:{value:'2026-12-02'}})
    fireEvent.click(screen.getByRole('button',{name:'Add task'}))
    await waitFor(()=>expect(taskCreates).toContainEqual({label:'Upload transcript',due_date:'2026-12-02',completed:false}))
    expect(await screen.findByLabelText('Due date for Upload transcript')).toHaveProperty('value','2026-12-02')
  })
})
