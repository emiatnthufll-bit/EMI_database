import React, { useEffect, useMemo, useState } from 'react'
import AdminUpload from './AdminUpload'

const API_URL = import.meta.env.VITE_API_URL || '/api'

function Chip({ label, onRemove }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm">
      {label}
      {onRemove && (
        <button onClick={onRemove} className="text-gray-500 hover:text-black">x</button>
      )}
    </span>
  )
}

function CollapsibleSection({ title, children, defaultOpen = false }) {
  const [isOpen, setIsOpen] = useState(defaultOpen)
  return (
    <div className="border-b last:border-b-0">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full py-2 px-1 hover:bg-gray-50 text-left font-medium text-gray-700"
      >
        <span>{title}</span>
        <span className={`transform transition-transform ${isOpen ? 'rotate-180' : ''}`}>v</span>
      </button>
      {isOpen && <div className="pl-2 pb-2">{children}</div>}
    </div>
  )
}

function FacetList({ items, selectedIds, onToggle }) {
  if (!items || items.length === 0) return <div className="text-sm text-gray-400 py-1">No items</div>
  return (
    <div className="grid grid-cols-1 gap-1 max-h-64 overflow-y-auto pr-1">
      {items.map((x) => (
        <label key={x.id} className="flex items-start gap-2 text-sm py-1 cursor-pointer hover:bg-gray-50 rounded">
          <input
            type="checkbox"
            checked={selectedIds.includes(x.id)}
            onChange={() => onToggle(x.id)}
            className="mt-0.5 shrink-0 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
          />
          <span className="min-w-0 flex-1 whitespace-normal break-words leading-snug" title={x.name}>{x.name}</span>
          <span className="shrink-0 text-gray-400 text-xs">{x.cnt ?? ''}</span>
        </label>
      ))}
    </div>
  )
}

function DetailField({ label, children }) {
  return (
    <div className="text-sm text-gray-700">
      <div className="font-semibold text-gray-900">{label}</div>
      <div className="mt-0.5 leading-relaxed">{children || 'N/A'}</div>
    </div>
  )
}

export default function App() {
  const isAdminPage = typeof window !== 'undefined' && window.location.pathname.startsWith('/admin')

  if (isAdminPage) {
    return <AdminUpload apiUrl={API_URL} />
  }

  const [q, setQ] = useState('')
  const [inputVal, setInputVal] = useState('')
  const [searchField, setSearchField] = useState('all')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [sort, setSort] = useState('year_desc')

  const [categories, setCategories] = useState([])
  const [keywords, setKeywords] = useState([])
  const [pubTypes, setPubTypes] = useState([])
  const [journals, setJournals] = useState([])
  const [natures, setNatures] = useState([])
  const [edus, setEdus] = useState([])
  const [locations, setLocations] = useState([])
  const [focuses, setFocuses] = useState([])

  const [selectedCats, setSelectedCats] = useState([])
  const [selectedKws, setSelectedKws] = useState([])
  const [selectedPubTypes, setSelectedPubTypes] = useState([])
  const [selectedJournals, setSelectedJournals] = useState([])
  const [selectedNatures, setSelectedNatures] = useState([])
  const [selectedEdus, setSelectedEdus] = useState([])
  const [selectedLocations, setSelectedLocations] = useState([])
  const [selectedFocuses, setSelectedFocuses] = useState([])

  const [yearFrom, setYearFrom] = useState('')
  const [yearTo, setYearTo] = useState('')

  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total, pageSize])

  const hasCategorySelections =
    selectedPubTypes.length ||
    selectedJournals.length ||
    selectedNatures.length ||
    selectedEdus.length ||
    selectedLocations.length ||
    selectedFocuses.length

  const clearCategorySelections = () => {
    setSelectedPubTypes([])
    setSelectedJournals([])
    setSelectedNatures([])
    setSelectedEdus([])
    setSelectedLocations([])
    setSelectedFocuses([])
    setPage(1)
  }

  const params = useMemo(() => {
    const p = new URLSearchParams()
    if (q) p.set('q', q)
    if (searchField !== 'all') p.set('field', searchField)
    selectedCats.forEach(id => p.append('category_ids', id))
    selectedKws.forEach(id => p.append('keyword_ids', id))
    selectedPubTypes.forEach(id => p.append('pub_type_ids', id))
    selectedJournals.forEach(id => p.append('journal_ids', id))
    selectedNatures.forEach(id => p.append('nature_ids', id))
    selectedEdus.forEach(id => p.append('edu_ids', id))
    selectedLocations.forEach(id => p.append('location_ids', id))
    selectedFocuses.forEach(id => p.append('focus_ids', id))
    if (yearFrom) p.set('year_from', yearFrom)
    if (yearTo) p.set('year_to', yearTo)
    p.set('page', page)
    p.set('page_size', pageSize)
    p.set('sort', sort)
    return p.toString()
  }, [q, searchField, selectedCats, selectedKws, selectedPubTypes, selectedJournals, selectedNatures, selectedEdus, selectedLocations, selectedFocuses, yearFrom, yearTo, page, pageSize, sort])

  useEffect(() => {
    const pf = new URLSearchParams()
    if (q) pf.set('q', q)
    selectedCats.forEach(id => pf.append('category_ids', id))
    selectedKws.forEach(id => pf.append('keyword_ids', id))
    selectedPubTypes.forEach(id => pf.append('pub_type_ids', id))
    selectedJournals.forEach(id => pf.append('journal_ids', id))
    selectedNatures.forEach(id => pf.append('nature_ids', id))
    selectedEdus.forEach(id => pf.append('edu_ids', id))
    selectedLocations.forEach(id => pf.append('location_ids', id))
    selectedFocuses.forEach(id => pf.append('focus_ids', id))
    if (yearFrom) pf.set('year_from', yearFrom)
    if (yearTo) pf.set('year_to', yearTo)

    fetch(`${API_URL}/facets?${pf}`)
      .then(r => r.json())
      .then(data => {
        setCategories(data.categories || [])
        setKeywords(data.keywords || [])
        setPubTypes(data.pub_types || [])
        setJournals(data.journals || [])
        setNatures(data.natures || [])
        setEdus(data.edus || [])
        setLocations(data.locations || [])
        setFocuses(data.focuses || [])
      })
      .catch(() => { })
  }, [q, selectedCats, selectedKws, selectedPubTypes, selectedJournals, selectedNatures, selectedEdus, selectedLocations, selectedFocuses, yearFrom, yearTo])

  useEffect(() => {
    fetch(`${API_URL}/search?${params}`)
      .then(r => r.json())
      .then(data => {
        setItems(data.items || [])
        setTotal(data.total || 0)
      })
      .catch(() => { })
  }, [params])

  const toggle = (setter) => (id) => {
    setPage(1)
    setter((prev) => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  function highlight(text, terms) {
    if (!text || !terms.length) return text
    const safe = terms.map(t => t.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&'))
    const regex = new RegExp(`(${safe.join('|')})`, 'ig')
    return String(text).split(regex).map((part, i) => (
      regex.test(part) ? <mark key={i}>{part}</mark> : <span key={i}>{part}</span>
    ))
  }

  const highlightTerms = useMemo(() => (q ? q.split(/\s+/).filter(Boolean) : []), [q])

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="sticky top-0 z-10 border-b" style={{ backgroundColor: 'rgb(181, 181, 182)' }}>
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center gap-4">
          <img src="/head.png" alt="School Logo" className="h-20 w-20 object-contain -my-4" />
          <div className="text-2xl font-bold" style={{ color: 'rgb(127, 16, 132)' }}>EMI Literature DB</div>
          <select
            value={searchField}
            onChange={e => setSearchField(e.target.value)}
            className="border rounded-xl px-3 py-2 bg-white font-medium"
            style={{ color: 'rgb(127, 16, 132)' }}
          >
            <option value="all">All fields</option>
            <option value="title">Title</option>
            <option value="abstract">Abstract</option>
            <option value="author">Author</option>
          </select>
          <input
            value={inputVal}
            onChange={e => setInputVal(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { setQ(inputVal); setPage(1) } }}
            className="flex-1 rounded-xl border px-4 py-2"
            placeholder="Search title/abstract/authors"
          />
          <button
            onClick={() => { setQ(inputVal); setPage(1) }}
            className="px-6 py-2 font-medium rounded-xl border-2 transition-colors"
            style={{ backgroundColor: 'rgb(127, 16, 132)', color: 'white', borderColor: 'rgb(127, 16, 132)' }}
            onMouseEnter={e => e.target.style.backgroundColor = 'rgb(107, 13, 112)'}
            onMouseLeave={e => e.target.style.backgroundColor = 'rgb(127, 16, 132)'}
          >
            Search
          </button>
          <select value={sort} onChange={e => setSort(e.target.value)} className="border rounded-xl px-3 py-2 bg-white font-medium" style={{ color: 'rgb(127, 16, 132)' }}>
            <option value="year_desc">Year desc</option>
            <option value="year_asc">Year asc</option>
          </select>
          <a
            href="/admin"
            className="px-4 py-2 font-medium rounded-xl border-2 transition-colors"
            style={{ backgroundColor: 'white', color: 'rgb(127, 16, 132)', borderColor: 'rgb(127, 16, 132)' }}
          >
            Admin
          </a>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 grid grid-cols-1 gap-6 lg:grid-cols-[380px_minmax(0,1fr)]">
        <aside className="min-w-0">
          <div className="rounded-2xl bg-white p-4 shadow-sm border overflow-y-auto max-h-[calc(100vh-150px)]">
            <h2 className="font-semibold mb-3">Filters</h2>
            <div className="mb-4 grid grid-cols-2 gap-2">
              <input type="number" value={yearFrom} onChange={e => { setYearFrom(e.target.value); setPage(1) }} placeholder="Year from" className="border rounded-xl px-3 py-2" />
              <input type="number" value={yearTo} onChange={e => { setYearTo(e.target.value); setPage(1) }} placeholder="Year to" className="border rounded-xl px-3 py-2" />
            </div>

            <div className="mb-6">
              <div className="flex items-center justify-between mb-2 border-b-2 border-purple-100 pb-1">
                <h3 className="font-bold text-lg text-purple-800">Categories</h3>
                <button
                  type="button"
                  onClick={clearCategorySelections}
                  disabled={!hasCategorySelections}
                  className={`text-xs px-2 py-1 rounded border ${
                    !hasCategorySelections
                      ? 'text-gray-400 border-gray-200 cursor-not-allowed'
                      : 'text-purple-700 border-purple-200 hover:bg-purple-50'
                  }`}
                >
                  Clear
                </button>
              </div>
              <div className="space-y-1">
                <CollapsibleSection title="Paper Type" defaultOpen={true}>
                  <FacetList items={pubTypes} selectedIds={selectedPubTypes} onToggle={toggle(setSelectedPubTypes)} />
                </CollapsibleSection>
                <CollapsibleSection title="Research Topics" defaultOpen={true}>
                  <FacetList items={journals} selectedIds={selectedJournals} onToggle={toggle(setSelectedJournals)} />
                </CollapsibleSection>
                <CollapsibleSection title="Research Results">
                  <FacetList items={natures} selectedIds={selectedNatures} onToggle={toggle(setSelectedNatures)} />
                </CollapsibleSection>
                <CollapsibleSection title="Research Methods">
                  <FacetList items={focuses} selectedIds={selectedFocuses} onToggle={toggle(setSelectedFocuses)} />
                </CollapsibleSection>
                <CollapsibleSection title="Research Setting">
                  <FacetList items={locations} selectedIds={selectedLocations} onToggle={toggle(setSelectedLocations)} />
                </CollapsibleSection>
                <CollapsibleSection title="Participants">
                  <FacetList items={edus} selectedIds={selectedEdus} onToggle={toggle(setSelectedEdus)} />
                </CollapsibleSection>
              </div>
            </div>
          </div>
        </aside>

        <section className="min-w-0">
          <div className="mb-3 flex flex-wrap gap-2">
            {selectedCats.length > 0 && <Chip label={`Topics: ${selectedCats.length}`} onRemove={() => setSelectedCats([])} />}
            {selectedKws.length > 0 && <Chip label={`Keywords: ${selectedKws.length}`} onRemove={() => setSelectedKws([])} />}
            {selectedPubTypes.length > 0 && <Chip label={`Paper Type: ${selectedPubTypes.length}`} onRemove={() => setSelectedPubTypes([])} />}
            {selectedJournals.length > 0 && <Chip label={`Research Topics: ${selectedJournals.length}`} onRemove={() => setSelectedJournals([])} />}
            {selectedNatures.length > 0 && <Chip label={`Research Results: ${selectedNatures.length}`} onRemove={() => setSelectedNatures([])} />}
            {selectedEdus.length > 0 && <Chip label={`Participants: ${selectedEdus.length}`} onRemove={() => setSelectedEdus([])} />}
            {selectedLocations.length > 0 && <Chip label={`Research Setting: ${selectedLocations.length}`} onRemove={() => setSelectedLocations([])} />}
            {selectedFocuses.length > 0 && <Chip label={`Research Methods: ${selectedFocuses.length}`} onRemove={() => setSelectedFocuses([])} />}
            {(yearFrom || yearTo) && <Chip label={`Year: ${yearFrom || 'any'}-${yearTo || 'any'}`} onRemove={() => { setYearFrom(''); setYearTo('') }} />}
          </div>

          <div className="rounded-2xl bg-white p-4 shadow-sm border">
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm text-gray-600">{total} results</div>
              <div className="flex items-center gap-2">
                <span className="text-sm">Page size</span>
                <select value={pageSize} onChange={e => { setPageSize(+e.target.value); setPage(1) }} className="border rounded-lg px-2 py-1">
                  {[10, 20, 50, 100].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
            </div>

            <ul className="space-y-4">
              {items.map(it => (
                <li key={it.id} className="border rounded-xl p-4 hover:shadow-md transition-shadow">
                  <div className="space-y-3">
                    <DetailField label="Paper Title">
                      <span className="font-semibold text-lg text-blue-600 hover:text-blue-800">
                        {it.url ? (
                          <a className="hover:underline" href={it.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
                            {highlight(it.title, highlightTerms)}
                          </a>
                        ) : highlight(it.title, highlightTerms)}
                      </span>
                    </DetailField>
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_120px]">
                      <DetailField label="Authors">{highlight(it.authors || 'N/A', highlightTerms)}</DetailField>
                      <DetailField label="Year">{it.year || 'N/A'}</DetailField>
                    </div>
                    <DetailField label="Publication Details">{it.venue || 'N/A'}</DetailField>
                    <DetailField label="Journal Quality">{it.journal_quality || 'N/A'}</DetailField>
                    <DetailField label="Abstract">
                      <p className="text-gray-800 leading-relaxed">{highlight(it.abstract || 'N/A', highlightTerms)}</p>
                    </DetailField>
                  </div>
                </li>
              ))}
            </ul>

            <div className="mt-6 flex items-center justify-between">
              <button disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))} className="px-3 py-2 rounded-lg border disabled:opacity-50">Prev</button>
              <div className="text-sm">Page {page} / {totalPages}</div>
              <button disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))} className="px-3 py-2 rounded-lg border disabled:opacity-50">Next</button>
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}
