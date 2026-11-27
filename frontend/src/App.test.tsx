// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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
  { id:3, outcome:'found', input_kind:'page', source_url:pages[2].url, attempted_at:'2026-11-25T01:00:02Z', suggestions:{ deadline:[], funding:[{heading:'Erasmus+ Scholarship Holders',excerpt:funding,financial_kind:'benefit'}], eligibility:[], documents:[], proposed_deadline:null } },
]

describe('EMMIR acceptance flow', () => {
  const extractBodies:unknown[]=[]
  const patchBodies:unknown[]=[]
  const sourceBodies:unknown[]=[]
  let currentItem={...item}

  beforeEach(() => {
    extractBodies.length=0
    patchBodies.length=0
    sourceBodies.length=0
    currentItem={...item}
    vi.stubGlobal('fetch',vi.fn(async(input:RequestInfo|URL,init?:RequestInit) => {
      const path=String(input)
      if(path.endsWith('/profile/current'))return new Response(JSON.stringify({nationality:null,prior_degree:null,field:null,target_intake:null,language_status:null}),{status:200})
      if(path.endsWith('/1/requirements'))return new Response(JSON.stringify([]),{status:200})
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
        const body=JSON.parse(String(init.body));patchBodies.push(body);currentItem={...currentItem,...body}
        return new Response(JSON.stringify(currentItem),{status:200})
      }
      if(path.includes('/api/tracked-scholarships?'))return new Response(JSON.stringify([currentItem]),{status:200})
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
    expect(screen.getAllByText('Clear copy of a valid passport').length).toBeGreaterThan(0)
    expect(screen.getAllByText('CV and Statement of Purpose').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Applicants must hold a relevant first degree/).length).toBeGreaterThan(0)
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

  it('keeps an extracted deadline out of the dashboard until it is selected and saved',async() => {
    render(<App/>)
    fireEvent.click(await screen.findByRole('button',{name:'Open'}))
    fireEvent.click(await screen.findByRole('button',{name:'Extract all source pages'}))
    await waitFor(()=>expect(extractBodies).toHaveLength(3))
    fireEvent.click(await screen.findByRole('button',{name:'Use deadline 2026-12-20'}))
    expect((screen.getByLabelText('Confirmed deadline') as HTMLInputElement).value).toBe('2026-12-20')
    expect(patchBodies).toHaveLength(0)
    fireEvent.click(screen.getByRole('button',{name:'Back to dashboard'}))
    expect(screen.getByText('Date not confirmed')).toBeTruthy()
    expect(screen.queryByText(/20 Dec 2026/)).toBeNull()

    fireEvent.click(screen.getByRole('button',{name:'Open'}))
    fireEvent.click(await screen.findByRole('button',{name:'Use deadline 2026-12-20'}))
    fireEvent.click(screen.getByRole('button',{name:'Save changes'}))
    await waitFor(()=>expect(patchBodies.at(-1)).toMatchObject({deadline:'2026-12-20'}))
    fireEvent.click(screen.getByRole('button',{name:'Back to dashboard'}))
    expect(await screen.findAllByText(/20 Dec 2026/)).not.toHaveLength(0)
  })

  it('lets the user edit and accept one sourced task',async()=>{
    vi.mocked(fetch).mockImplementation(async(input:RequestInfo|URL,init?:RequestInit)=>{
      const path=String(input)
      if(path.endsWith('/1/extract')){extractBodies.push({});return new Response(JSON.stringify(attempts[0]))}
      if(path.endsWith('/1/extraction'))return new Response(JSON.stringify({latest:attempts[0],previous_found:null,official_pages:pages,page_attempts:[attempts[0]]}))
      if(path.endsWith('/1/accept-proposal')){patchBodies.push(JSON.parse(String(init?.body)));return new Response(JSON.stringify({id:9,already_accepted:false}))}
      if(path.endsWith('/1'))return new Response(JSON.stringify(currentItem))
      if(path.includes('/api/tracked-scholarships?'))return new Response(JSON.stringify([currentItem]))
      throw new Error(path)
    })
    render(<App/>);fireEvent.click(await screen.findByRole('button',{name:'Open'}))
    const proposals=await screen.findByRole('region',{name:'Proposed checklist tasks'})
    expect(within(proposals).getAllByRole('link',{name:'Official source ↗'})[0].getAttribute('href')).toBe(pages[0].url)
    fireEvent.change(within(proposals).getByLabelText('Task wording: Clear copy of a valid passport'),{target:{value:'Prepare passport copy'}})
    expect(patchBodies).toHaveLength(0)
    fireEvent.click(within(proposals).getAllByRole('button',{name:'Accept task'})[0])
    await waitFor(()=>expect(patchBodies[0]).toMatchObject({label:'Prepare passport copy',excerpt:'Clear copy of a valid passport'}))
  })

  it('labels costs separately and does not offer them as scholarship funding',async()=>{
    const costAttempt={...attempts[2],suggestions:{...attempts[2].suggestions,funding:[{heading:'Participation Costs',excerpt:'The participation costs cover programme activities.',financial_kind:'cost'},{heading:'Scholarship holders',excerpt:'Scholarship holders receive a stipend but pay travel costs.',financial_kind:'mixed'}]}}
    vi.mocked(fetch).mockImplementation(async(input:RequestInfo|URL)=>{
      const path=String(input)
      if(path.endsWith('/profile/current'))return new Response(JSON.stringify({nationality:null,prior_degree:null,field:null,target_intake:null,language_status:null}))
      if(path.endsWith('/1/requirements'))return new Response('[]')
      if(path.endsWith('/1/extraction'))return new Response(JSON.stringify({latest:costAttempt,previous_found:null,official_pages:pages,page_attempts:[costAttempt]}))
      if(path.includes('/api/tracked-scholarships?'))return new Response(JSON.stringify([currentItem]))
      throw new Error(path)
    })
    render(<App/>);fireEvent.click(await screen.findByRole('button',{name:'Open'}))
    expect(await screen.findByText('Fees or costs — not confirmed funding')).toBeTruthy()
    expect(screen.getByText('Benefits and costs — review both')).toBeTruthy()
    expect(screen.queryByRole('button',{name:'Use as funding'})).toBeNull()
  })

  it('lets the user save profile facts and review an extracted source requirement',async()=>{
    const requests:unknown[]=[]
    vi.mocked(fetch).mockImplementation(async(input:RequestInfo|URL,init?:RequestInit)=>{
      const path=String(input)
      if(path.endsWith('/profile/current')){if(init?.method==='PUT')requests.push(JSON.parse(String(init.body)));return new Response(JSON.stringify({nationality:null,prior_degree:null,field:null,target_intake:null,language_status:null}))}
      if(path.endsWith('/1/requirements')){if(init?.method==='POST'){requests.push(JSON.parse(String(init.body)));return new Response(JSON.stringify({id:1}))}return new Response(JSON.stringify([]))}
      if(path.endsWith('/1/extraction'))return new Response(JSON.stringify({latest:attempts[1],previous_found:null,official_pages:pages,page_attempts:[attempts[1]]}))
      if(path.includes('/api/tracked-scholarships?'))return new Response(JSON.stringify([currentItem]))
      throw new Error(path)
    })
    render(<App/>);fireEvent.click(await screen.findByRole('button',{name:'Open'}))
    const checker=await screen.findByRole('region',{name:'Application checker'})
    fireEvent.change(within(checker).getByLabelText('Nationality'),{target:{value:'Thai'}})
    fireEvent.click(within(checker).getByRole('button',{name:'Save profile'}))
    await waitFor(()=>expect(requests).toContainEqual(expect.objectContaining({nationality:'Thai'})))
    fireEvent.change(within(checker).getByLabelText('Source excerpt'),{target:{value:'2:0'}})
    fireEvent.change(within(checker).getByLabelText('Exact source wording'),{target:{value:'first degree'}})
    fireEvent.click(within(checker).getByRole('button',{name:'Add requirement'}))
    await waitFor(()=>expect(requests).toContainEqual(expect.objectContaining({attempt_id:2,expected:'first degree'})))
  })
})
