// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import App from './App'

afterEach(()=>{cleanup();vi.unstubAllGlobals()})

it('saves a URL, extracts a sourced task, accepts it, and updates the dashboard',async()=>{
  const url='https://example.org/scholarship'
  let item={id:1,source_url:url,title:null,provider:null,intake:null,deadline:null,funding:null,eligibility:null,notes:null,status:'saved',archived_at:null,checklist:[] as {id:number;label:string;completed:boolean;due_date:string|null}[]}
  const attempt={id:5,outcome:'found',input_kind:'page',source_url:url,attempted_at:'2026-11-25T01:00:00Z',suggestions:{documents:[{heading:'Required documents',excerpt:'A copy of your passport'}],eligibility:[],deadline:[],funding:[],application_steps:[]}}
  let saved=false,extracted=false
  vi.stubGlobal('fetch',vi.fn(async(input:RequestInfo|URL,init?:RequestInit)=>{
    const path=String(input),method=init?.method||'GET'
    if(path.endsWith('/profile/current'))return new Response(JSON.stringify({nationality:null,prior_degree:null,field:null,target_intake:null,language_status:null}))
    if(path.endsWith('/1/requirements'))return new Response('[]')
    if(path.endsWith('/1/extraction'))return new Response(JSON.stringify({latest:extracted?attempt:null,previous_found:null,official_pages:[{id:null,label:'Saved scholarship page',url,removable:false}],page_attempts:extracted?[attempt]:[]}))
    if(path.endsWith('/1/extract')){extracted=true;return new Response(JSON.stringify(attempt))}
    if(path.endsWith('/1/accept-proposal')){const body=JSON.parse(String(init?.body));item={...item,checklist:[{id:1,label:body.label,completed:false,due_date:null}]};return new Response(JSON.stringify({id:1,already_accepted:false}))}
    if(path.endsWith('/1'))return new Response(JSON.stringify(item))
    if(path.endsWith('/api/tracked-scholarships')&&method==='POST'){saved=true;return new Response(JSON.stringify(item),{status:201})}
    if(path.includes('/api/tracked-scholarships?'))return new Response(JSON.stringify(saved?[item]:[]))
    throw new Error(path)
  }))
  render(<App/>)
  fireEvent.change(screen.getByLabelText('Scholarship URL'),{target:{value:url}})
  fireEvent.click(screen.getByRole('button',{name:'Save scholarship'}))
  const extract=await screen.findByRole('button',{name:'Extract all source pages'})
  await waitFor(()=>expect((extract as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(extract)
  const proposals=await screen.findByRole('region',{name:'Proposed checklist tasks'})
  expect(within(proposals).getByRole('link',{name:'Official source ↗'}).getAttribute('href')).toBe(url)
  fireEvent.change(within(proposals).getByLabelText('Task wording: A copy of your passport'),{target:{value:'Prepare passport'}})
  fireEvent.click(within(proposals).getByRole('button',{name:'Accept task'}))
  await screen.findByDisplayValue('Prepare passport')
  fireEvent.click(screen.getByRole('button',{name:'Back to dashboard'}))
  expect(await screen.findByText('0/1 tasks complete')).toBeTruthy()
  expect(screen.getByText('Date not confirmed')).toBeTruthy()
})
