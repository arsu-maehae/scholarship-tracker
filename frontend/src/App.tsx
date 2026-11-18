import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'
import { countryCodes } from './countries'
import './filters.css'

type Scheme = { id: number; name: string; slug: string }
type Scholarship = {
  id: number; title: string; scheme: { name: string; slug: string }
  cycle: string | null; intake_year: number | null
  countries: string[] | null; degree_levels: string[] | null
  description: string | null
  fields_of_study: string[] | null; funding_category: string
  field_match?: 'not_filtered' | 'exact' | 'unverified'
  funding_notes: string | null; call_status: string
  official_url: string | null; last_checked: string | null
}
type Page = { total: number; limit: number; offset: number; items: Scholarship[] }
type Filters = { q: string; country: string; degree: string; field: string; funding: string; scheme: string; intake_year: string }
type Results = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; page: Page }
const emptyFilters: Filters = { q: '', country: '', degree: '', field: '', funding: '', scheme: '', intake_year: '' }
const labels: Record<string, string> = {
  bachelor: "Bachelor's", master: "Master's", phd: 'PhD', master_phd: 'Combined master’s / PhD',
  full: 'Full funding', tuition_only: 'Tuition only', partial: 'Partial funding', unknown: 'Unverified',
  ai: 'Artificial intelligence', 'data-science': 'Data science', 'software-engineering': 'Software engineering',
  robotics: 'Robotics', cybersecurity: 'Cybersecurity', 'computer-science': 'Computer science',
  engineering: 'Engineering', mathematics: 'Mathematics', 'natural-sciences': 'Natural sciences',
}
const countryNames = new Intl.DisplayNames(['en'], { type: 'region' })
const label = (value: string) => labels[value] ?? value.replaceAll('-', ' ')
const countryName = (value: string) => countryNames.of(value) ?? value
const countries = countryCodes.map(code => ({ code, name: countryName(code) }))
  .sort((a, b) => a.name.localeCompare(b.name, 'en'))
function officialLink(value: string | null) {
  if (!value) return null
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : null } catch { return null }
}
async function getJson<T>(url: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal })
  if (!response.ok) throw new Error(`Request failed (${response.status}). Check that the backend is running and try again.`)
  return response.json() as Promise<T>
}

type WebItem = { title: string; url: string; source: string; snippet: string }
type AiPreferences = { filters: Partial<Record<keyof Filters, string | number>>; unsupported: string[] }
type WebResults = { status: 'idle' } | { status: 'loading'; query: string } | { status: 'error'; query: string } | { status: 'ready'; query: string; items: WebItem[] }
function WebOpportunities({ result, retry }: { result: WebResults; retry: (query: string) => void }) {
  return <section className="web-opportunities" aria-labelledby="web-heading">
    <h2 id="web-heading">More opportunities from the web</h2>
    <p>Web results are unverified suggestions, not confirmed matches. Your filters are used as search terms; eligibility, funding, dates and study destination must be checked on the official source.</p>
    {result.status !== 'idle' && <p className="web-query">Search: {result.query}</p>}
    {result.status === 'idle' && <p>Web discovery is currently unavailable. Gemini searches the catalogue above.</p>}
    {result.status === 'loading' && <p role="status">Searching the web…</p>}
    {result.status === 'error' && <div role="status"><p>Web search is unavailable. Check the search service setup and try again.</p><button type="button" className="primary-button" onClick={() => retry(result.query)}>Retry web search</button></div>}
    {result.status === 'ready' && result.items.length === 0 && <p>No web suggestions found. Try a different search.</p>}
    {result.status === 'ready' && result.items.map(item => { const url = officialLink(item.url); return url && <article className="web-result" key={url}><span>Unverified · {item.source}</span><h3><a href={url} target="_blank" rel="noopener noreferrer">{item.title} ↗<span className="sr-only"> (opens in a new tab)</span></a></h3><p>{item.snippet}</p></article> })}
  </section>
}

export default function App() {
  const [draft, setDraft] = useState<Filters>(emptyFilters)
  const [query, setQuery] = useState('limit=20&offset=0')
  const [retry, setRetry] = useState(0)
  const [schemes, setSchemes] = useState<Scheme[]>([])
  const [schemeError, setSchemeError] = useState(false)
  const [fields, setFields] = useState<string[]>([])
  const [fieldOptionsStatus, setFieldOptionsStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [includeUnknownFields, setIncludeUnknownFields] = useState(true)
  const [results, setResults] = useState<Results>({ status: 'loading' })
  const [resultQuery, setResultQuery] = useState('')
  const [webResults, setWebResults] = useState<WebResults>({ status: 'idle' })
  const webController = useRef<AbortController | null>(null)
  const aiController = useRef<AbortController | null>(null)
  const [aiStatus, setAiStatus] = useState<'idle' | 'loading' | 'error' | 'ready'>('idle')
  const [aiMessage, setAiMessage] = useState('')
  const [searchBlocked, setSearchBlocked] = useState(false)
  const loading = results.status === 'loading' || resultQuery !== query

  useEffect(() => () => webController.current?.abort(), [])
  useEffect(() => () => aiController.current?.abort(), [])

  function findWeb(query: string) {
    webController.current?.abort()
    const controller = new AbortController()
    webController.current = controller
    setWebResults({ status: 'loading', query })
    getJson<{ items: WebItem[] }>(`/api/web-opportunities?${new URLSearchParams({ q: query })}`, controller.signal)
      .then(data => { if (!controller.signal.aborted) setWebResults({ status: 'ready', query, items: data.items }) })
      .catch(() => { if (!controller.signal.aborted) setWebResults({ status: 'error', query }) })
  }

  useEffect(() => {
    const controller = new AbortController()
    getJson<{ fields: string[] }>('/api/filter-options', controller.signal).then(data => {
      if (!Array.isArray(data.fields) || data.fields.some(value => typeof value !== 'string')) throw new Error('Unexpected field options')
      if (!controller.signal.aborted) { setFields(data.fields); setFieldOptionsStatus('ready') }
    }).catch(() => { if (!controller.signal.aborted) setFieldOptionsStatus('error') })
    return () => controller.abort()
  }, [retry])

  useEffect(() => {
    const controller = new AbortController()
    getJson<Scheme[]>('/api/schemes', controller.signal).then(data => {
      if (!controller.signal.aborted) { setSchemes(data); setSchemeError(false) }
    }).catch(() => { if (!controller.signal.aborted) setSchemeError(true) })
    return () => controller.abort()
  }, [retry])

  useEffect(() => {
    const controller = new AbortController()
    getJson<Page>(`/api/scholarships?${query}`, controller.signal).then(page => {
      if (!Array.isArray(page.items) || typeof page.total !== 'number') throw new Error('Unexpected API response.')
      if (!controller.signal.aborted) { setResults({ status: 'ready', page }); setResultQuery(query) }
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) {
        setResults({ status: 'error', message: error instanceof Error ? error.message : 'Could not load scholarships.' })
        setResultQuery(query)
      }
    })
    return () => controller.abort()
  }, [query, retry])

  function update(key: keyof Filters, value: string) {
    aiController.current?.abort(); setAiStatus('idle'); setAiMessage('')
    setDraft(current => ({ ...current, [key]: value }))
  }
  function applyFilters(selected: Filters, related?: { name: string; code: string }) {
    setSearchBlocked(false)
    const params = new URLSearchParams({ limit: '20', offset: '0' })
    Object.entries(selected).forEach(([key, value]) => {
      const cleaned = value.trim()
      if (cleaned) params.set(key, key === 'country' ? cleaned.toUpperCase() : cleaned.toLowerCase())
    })
    if (selected.field && includeUnknownFields) params.set('include_unknown_fields', 'true')
    if (related) { params.set('related', related.name); params.set('related_country', related.code) }
    const next = params.toString()
    setQuery(next)
    setResults({ status: 'loading' })
    setRetry(value => value + 1)
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    aiController.current?.abort(); setAiStatus('idle'); setAiMessage('')
    applyFilters(draft)
  }
  async function interpretSearch() {
    const text = draft.q.trim()
    setSearchBlocked(true)
    if (!text) { setAiStatus('error'); setAiMessage('Enter a request in Keywords first.'); return }
    aiController.current?.abort()
    const country = countries.find(item => item.name.toLocaleLowerCase('en') === text.toLocaleLowerCase('en'))
    if (country) {
      const next = { ...draft, q: '' }
      setDraft(next); setAiStatus('ready')
      setAiMessage(`Searching for catalogue entries related to ${country.name}. Check the source for eligibility and study destination.`)
      applyFilters(next, country)
      return
    }
    const controller = new AbortController()
    aiController.current = controller
    setAiStatus('loading'); setAiMessage('')
    try {
      const response = await fetch('/api/catalogue-preferences', { method: 'POST', signal: controller.signal,
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'ScholarshipDiscovery' }, body: JSON.stringify({ text }) })
      if (!response.ok) {
        const data = await response.json().catch(() => ({})) as { detail?: string }
        throw new Error(data.detail ?? 'Could not interpret the request.')
      }
      const data = await response.json() as AiPreferences
      if (controller.signal.aborted) return
      if (data.unsupported.length) { setAiStatus('error'); setAiMessage(`Please clarify: ${data.unsupported.join('; ')}`); return }
      const next: Filters = { ...draft, q: '' }
      for (const [key, value] of Object.entries(data.filters) as [keyof Filters, string | number][]) {
        const textValue = String(value)
        if (key !== 'q' && next[key] && next[key] !== textValue) {
          setAiStatus('error'); setAiMessage(`Your selected ${key.replace('_', ' ')} conflicts with the request. Please adjust it.`); return
        }
        next[key] = textValue
      }
      setDraft(next); setAiStatus('ready')
      const summary = Object.entries(next).filter(([, value]) => value).map(([key, value]) => `${key === 'country' ? 'Study country' : key.replace('_', ' ')}: ${key === 'country' ? countryName(value) : label(value)}`).join(' · ')
      setAiMessage(`Searching the catalogue using: ${summary || 'no filters'}. Check these filters before relying on results.`)
      applyFilters(next)
    } catch (error) {
      if (!controller.signal.aborted) { setAiStatus('error'); setAiMessage(error instanceof Error ? error.message : 'Could not interpret the request.') }
    }
  }
  function reset() {
    setDraft(emptyFilters); setIncludeUnknownFields(true); setQuery('limit=20&offset=0')
    setSearchBlocked(false)
    aiController.current?.abort(); setAiStatus('idle'); setAiMessage('')
    webController.current?.abort(); setWebResults({ status: 'idle' })
    setResults({ status: 'loading' }); setRetry(value => value + 1)
  }
  function paginate(offset: number) {
    const params = new URLSearchParams(query)
    params.set('offset', String(offset)); setQuery(params.toString())
    document.getElementById('results-heading')?.focus()
  }
  const page = results.status === 'ready' && !loading && !searchBlocked ? results.page : null

  return <>
    <header className="site-header"><a className="brand" href="/">Scholarship<span>Discovery</span></a><span className="early-label">Early catalogue</span></header>
    <main>
      <section className="intro"><p className="eyebrow">YOUR NEXT CHAPTER</p><h1>Find a scholarship.<br /><span>Open a new possibility.</span></h1><p>Explore study opportunities by destination, degree and funding.</p></section>
      <div className="workspace">
        <aside className="filter-panel"><div className="panel-heading"><h2>Refine your search</h2><button type="button" className="text-button" onClick={reset}>Reset</button></div>
          <form onSubmit={submit}>
            <label htmlFor="keywords">Keywords</label><input id="keywords" type="search" maxLength={100} placeholder="Scholarship or subject" value={draft.q} onChange={e => update('q', e.target.value)} />
            <small>For a manual search, use Study country for destinations; keywords search titles and descriptions.</small>
            <button className="ai-search-button" type="button" onClick={interpretSearch} disabled={aiStatus === 'loading'}>{aiStatus === 'loading' ? 'Interpreting…' : 'Search with Gemini'}</button>
            <small>Interprets your request to search this catalogue. It does not search the live web.</small>
            {aiMessage && <small role={aiStatus === 'error' ? 'alert' : 'status'}>{aiMessage}</small>}
            <label htmlFor="country">Study country</label>
            <select id="country" value={draft.country} onChange={e => update('country', e.target.value)} aria-describedby="country-help"><option value="">Any country</option>{countries.map(country => <option key={country.code} value={country.code}>{country.name}</option>)}</select>
            <small id="country-help">Study destination. A listed country may have no indexed scholarships yet.</small>
            <label htmlFor="degree">Degree level</label><select id="degree" value={draft.degree} onChange={e => update('degree', e.target.value)}><option value="">Any degree</option>{['bachelor', 'master', 'phd', 'master_phd'].map(value => <option key={value} value={value}>{label(value)}</option>)}</select>
            <label htmlFor="field">Programme / field</label><select id="field" value={draft.field} onChange={e => update('field', e.target.value)} aria-describedby="field-help" disabled={fieldOptionsStatus !== 'ready'}><option value="">{fieldOptionsStatus === 'loading' ? 'Loading fields…' : 'Any field'}</option>{fields.map(value => <option key={value} value={value}>{label(value)}</option>)}</select>
            <small id="field-help">Choices come from indexed fields, not every possible subject.</small>
            {fieldOptionsStatus === 'error' && <small role="alert">Field choices could not load. Update backend/main.py and restart FastAPI. <button className="text-button" type="button" onClick={() => setRetry(value => value + 1)}>Retry fields</button></small>}
            <label className="unknown-field-choice" htmlFor="include-unknown"><input id="include-unknown" type="checkbox" checked={includeUnknownFields} onChange={e => setIncludeUnknownFields(e.target.checked)} disabled={!draft.field} /><span>Include possible matches with unrecorded fields</span></label>
            <small>Possible matches need a subject check on the official website. Apply changes with Find scholarships.</small>
            <label htmlFor="funding">Funding coverage</label><select id="funding" value={draft.funding} onChange={e => update('funding', e.target.value)}><option value="">Any funding</option>{['full', 'tuition_only', 'partial', 'unknown'].map(value => <option key={value} value={value}>{label(value)}</option>)}</select>
            <label htmlFor="scheme">Scholarship scheme</label><select id="scheme" value={draft.scheme} onChange={e => update('scheme', e.target.value)}><option value="">All schemes</option>{schemes.map(scheme => <option key={scheme.slug} value={scheme.slug}>{scheme.name}</option>)}</select>
            {schemeError && <small role="alert">Scheme choices could not load. <button className="text-button" type="button" onClick={() => setRetry(value => value + 1)}>Retry</button></small>}
            <label htmlFor="year">Intake year</label><input id="year" type="number" min={1900} max={2200} step={1} placeholder="Any year" value={draft.intake_year} onChange={e => update('intake_year', e.target.value)} />
            <button className="primary-button search-button" type="submit">Find scholarships <span aria-hidden="true">→</span></button>
          </form>
        </aside>
        <section className="results-panel" aria-labelledby="results-heading" aria-busy={loading}>
          <div className="results-heading"><div><p className="eyebrow">EXPLORE OPPORTUNITIES</p><h2 id="results-heading" tabIndex={-1}>Scholarships</h2></div><span className="result-count" role="status">{searchBlocked ? 'Search not completed' : loading ? 'Searching…' : page ? `${page.total} ${page.total === 1 ? 'result' : 'results'}` : 'Unavailable'}</span></div>
          <p className="coverage-note">Results come from the scholarships currently in our database. Coverage is growing; this is not a complete worldwide catalogue. An unverified call status does not confirm applications are open.</p>
          {new URLSearchParams(query).has('related') && <p className="field-search-note">Related to {new URLSearchParams(query).get('related')}: includes recorded destinations and mentions in the catalogue. This does not confirm nationality or eligibility, and other opportunities may exist.</p>}
          {new URLSearchParams(query).has('field') && <p className="field-search-note">{new URLSearchParams(query).get('include_unknown_fields') === 'true' ? 'Showing recorded field matches first, then possible matches whose fields are unrecorded. Possible matches do not confirm eligibility.' : 'Showing recorded field matches only. Opportunities with unrecorded fields are excluded.'}</p>}
          {searchBlocked && <div className="state-card" role="status">{aiStatus === 'loading' ? 'Interpreting your request…' : 'Search not completed. Check the message in the search panel and adjust your request.'}</div>}
          {!searchBlocked && loading && <div className="state-card" role="status">Loading opportunities…</div>}
          {!searchBlocked && !loading && results.status === 'error' && <div className="state-card" role="alert"><h3>We couldn’t load the catalogue</h3><p>{results.message}</p><button className="primary-button" onClick={() => { setResults({ status: 'loading' }); setRetry(value => value + 1) }}>Try again</button></div>}
          {page?.items.length === 0 && <div className="state-card"><div className="empty-symbol" aria-hidden="true">⌕</div><h3>No matching scholarships yet</h3><p>Try fewer filters. A zero result means no matching entry in this database; other scholarships may exist.</p><button className="primary-button" onClick={reset}>Clear filters</button></div>}
          {page && page.items.map(item => {
            const url = officialLink(item.official_url)
            return <article className="scholarship-card" key={item.id}>
              <div className="card-top"><p className="scheme-name">{item.scheme.name}</p><span className={`status-badge status-${['open', 'upcoming', 'closed'].includes(item.call_status) ? item.call_status : 'unknown'}`}>{item.call_status === 'unknown' ? 'Call unverified' : item.call_status === 'open' ? 'Call open' : item.call_status === 'upcoming' ? 'Upcoming call' : item.call_status === 'closed' ? 'Call closed' : 'Call unverified'}</span></div>
              <h3>{item.title}</h3><p className="cycle">{item.cycle ?? 'Cycle not recorded'}{item.intake_year ? ` · ${item.intake_year} intake` : ''}</p>
              {item.field_match === 'exact' && <p className="field-match-note">Selected field is recorded. Check course and personal eligibility.</p>}
              {item.field_match === 'unverified' && <p className="field-match-note field-unverified">Possible match — fields unrecorded. Check whether your subject is supported.</p>}
              <div className="tags"><span className="funding-tag">{label(item.funding_category)}</span>{item.degree_levels?.map(degree => <span key={degree}>{label(degree)}</span>)}</div>
              <dl className="card-facts"><div><dt>Study destinations</dt><dd>{item.countries?.length ? item.countries.map(countryName).join(' · ') : 'Not recorded'}</dd></div><div><dt>Fields of study</dt><dd>{item.fields_of_study?.length ? item.fields_of_study.map(label).join(' · ') : 'Not recorded'}</dd></div></dl>
              <details className="scholarship-details"><summary>View scholarship details</summary>
                <div className="detail-section"><h4>About and eligibility</h4><p>{item.description ?? 'Eligibility details have not been recorded.'}</p></div>
                <div className="detail-section"><h4>Funding and costs</h4><p>{item.funding_notes ?? 'Funding details have not been recorded.'}</p></div>
                <div className="detail-section"><h4>Dates and application</h4><p>Intake: {item.intake_year ?? 'Not recorded'}. Application deadline: not recorded. Check the official source for the current call and deadline.</p></div>
                <p className="source-note">Source last checked: {item.last_checked ?? 'Not recorded'}. The official source has the current requirements and award terms.</p>
              </details>
              <div className="card-footer"><span>Check official requirements</span>{url ? <a className="official-link" href={url} target="_blank" rel="noopener noreferrer">Official website <span aria-hidden="true">↗</span><span className="sr-only"> (opens in a new tab)</span></a> : <span>Official link not recorded</span>}</div>
            </article>
          })}
          {page && page.total > page.limit && <nav className="pagination" aria-label="Result pages"><button disabled={page.offset === 0} onClick={() => paginate(Math.max(0, page.offset - page.limit))}>Previous</button><span>{page.offset + 1}–{Math.min(page.offset + page.limit, page.total)} of {page.total}</span><button disabled={page.offset + page.limit >= page.total} onClick={() => paginate(page.offset + page.limit)}>Next</button></nav>}
          <WebOpportunities result={webResults} retry={findWeb} />
        </section>
      </div>
    </main><footer className="site-footer">Scholarship Discovery · Built to make your next step clearer.</footer>
  </>
}
