// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from './App'

const item = { id:1, source_url:'https://www.emmir.org/', title:null, provider:null, intake:null, deadline:null, funding:null, eligibility:null, notes:null, status:'saved', archived_at:null, checklist:[] }
const pages = [
  { id:null, label:'Application deadlines and required documents', url:'https://www.emmir.org/application-procedures', removable:false },
  { id:null, label:'Entry and language requirements', url:'https://www.emmir.org/requirements', removable:false },
  { id:null, label:'Costs and funding', url:'https://www.emmir.org/cost-and-funding', removable:false },
]
const funding = 'Scholarship holders receive a monthly scholarship of 1400€ for 24 months.'
const attempts = [
  { id:1, outcome:'found', input_kind:'page', source_url:pages[0].url, attempted_at:'2026-11-25T01:00:00Z', suggestions:{ deadline:[
    {heading:'Application deadlines',excerpt:'20 December 2026 for scholarship and non-fee paying self-funded applicants',date:'2026-12-20'},
    {heading:'Application deadlines',excerpt:'15 July 2027 for fee paying self-funded applicants',date:'2027-07-15'},
  ], funding:[], eligibility:[], documents:[
    {heading:'Required documentation',excerpt:'Clear copy of a valid passport'},
    {heading:'Required documentation',excerpt:'CV and Statement of Purpose'},
  ], proposed_deadline:null } },
  { id:2, outcome:'found', input_kind:'page', source_url:pages[1].url, attempted_at:'2026-11-25T01:00:01Z', suggestions:{ deadline:[], funding:[], eligibility:[{heading:'Entry requirements',excerpt:'Applicants must hold a relevant first degree.'}], documents:[], proposed_deadline:null } },
  { id:3, outcome:'found', input_kind:'page', source_url:pages[2].url, attempted_at:'2026-11-25T01:00:02Z', suggestions:{ deadline:[], funding:[{heading:'Erasmus+ Scholarship Holders',excerpt:funding}], eligibility:[], documents:[], proposed_deadline:null } },
]

describe('EMMIR acceptance flow', () => {
  const extractBodies:unknown[]=[]
  const patchBodies:unknown[]=[]
  const sourceBodies:unknown[]=[]

  beforeEach(() => {
    extractBodies.length=0
    patchBodies.length=0
    sourceBodies.length=0
    vi.stubGlobal('fetch',vi.fn(async(input:RequestInfo|URL,init?:RequestInit) => {
      const path=String(input)
      if(path.endsWith('/1/extract')&&init?.method==='POST'){
        extractBodies.push(JSON.parse(String(init.body)))
        return new Response(JSON.stringify(attempts[Math.min(extractBodies.length-1,2)]),{status:200})
      }
      if(path.endsWith('/1/extraction')){
        const complete=extractBodies.length===3
        const added=sourceBodies.length?{id:4,label:'scholarships.example.org/funding',url:'https://scholarships.example.org/funding',removable:true}:null
        return new Response(JSON.stringify({latest:complete?attempts[2]:null,previous_found:null,official_pages:added?[...pages,added]:pages,page_attempts:complete?attempts:[]}),{status:200})
      }
      if(path.endsWith('/1/sources')&&init?.method==='POST'){
        const body=JSON.parse(String(init.body));sourceBodies.push(body)
        return new Response(JSON.stringify({id:4,...body}),{status:201})
      }
      if(path.endsWith('/1')&&init?.method==='PATCH'){
        const body=JSON.parse(String(init.body));patchBodies.push(body)
        return new Response(JSON.stringify({...item,...body}),{status:200})
      }
      if(path.includes('/api/tracked-scholarships?'))return new Response(JSON.stringify([item]),{status:200})
      throw new Error(`Unexpected request: ${init?.method||'GET'} ${path}`)
    }))
  })

  afterEach(() => { cleanup();vi.unstubAllGlobals() })

  it('aggregates sourced excerpts and saves an applied suggestion only on Save changes',async() => {
    render(<App/>)
    fireEvent.click(await screen.findByRole('button',{name:'Open'}))
    const extract=await screen.findByRole('button',{name:'Extract all source pages'})
    await waitFor(()=>expect((extract as HTMLButtonElement).disabled).toBe(false))
    expect((screen.getByLabelText('Confirmed deadline') as HTMLInputElement).value).toBe('')
    fireEvent.click(extract)
    await waitFor(()=>expect(extractBodies).toHaveLength(3))
    expect(extractBodies.map(body=>(body as {source_url:string}).source_url)).toEqual(pages.map(page=>page.url))
    expect(await screen.findByText(/20 December 2026 for scholarship/)).toBeTruthy()
    expect(screen.getByText(/15 July 2027 for fee paying/)).toBeTruthy()
    expect(screen.getByText('Clear copy of a valid passport')).toBeTruthy()
    expect(screen.getByText('CV and Statement of Purpose')).toBeTruthy()
    expect(screen.getByText(/Applicants must hold a relevant first degree/)).toBeTruthy()
    expect(screen.getByText(funding)).toBeTruthy()
    expect(screen.getByRole('button',{name:'Use deadline 2026-12-20'})).toBeTruthy()
    expect(screen.getByRole('button',{name:'Use deadline 2027-07-15'})).toBeTruthy()
    expect(screen.getAllByRole('link',{name:'Source page ↗'})).toHaveLength(6)
    expect((screen.getByLabelText('Confirmed deadline') as HTMLInputElement).value).toBe('')

    fireEvent.click(screen.getByRole('button',{name:'Use as funding'}))
    expect((screen.getByLabelText('Funding') as HTMLTextAreaElement).value).toBe(funding)
    expect((screen.getByRole('button',{name:'Added to draft ✓'}) as HTMLButtonElement).disabled).toBe(true)
    expect(screen.getByText('Funding added to the draft. It is not saved yet.')).toBeTruthy()
    expect(patchBodies).toHaveLength(0)
    expect((screen.getByLabelText('Confirmed deadline') as HTMLInputElement).value).toBe('')

    fireEvent.click(screen.getByRole('button',{name:'Save changes'}))
    await waitFor(()=>expect(patchBodies).toHaveLength(1))
    expect(patchBodies[0]).toMatchObject({funding,deadline:null})
    expect(await screen.findByText('Changes saved ✓')).toBeTruthy()
  })

  it('adds an additional official source page without changing confirmed fields',async() => {
    render(<App/>)
    fireEvent.click(await screen.findByRole('button',{name:'Open'}))
    const input=await screen.findByLabelText('Additional official source URL')
    fireEvent.change(input,{target:{value:'https://scholarships.example.org/funding'}})
    fireEvent.click(screen.getByRole('button',{name:'Add source page'}))
    await waitFor(()=>expect(sourceBodies).toHaveLength(1))
    expect(await screen.findByRole('link',{name:'scholarships.example.org/funding ↗'})).toBeTruthy()
    expect((screen.getByLabelText('Confirmed deadline') as HTMLInputElement).value).toBe('')
    expect(patchBodies).toHaveLength(0)
  })
})
