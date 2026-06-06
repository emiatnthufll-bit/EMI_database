import React, { useState } from 'react'

export default function AdminUpload({ apiUrl }) {
  const [token, setToken] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setResult(null)

    if (!file) {
      setError('Please select a .xlsx file')
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    setLoading(true)
    try {
      const response = await fetch(`${apiUrl}/admin/upload-excel`, {
        method: 'POST',
        headers: {
          'X-Admin-Token': token,
        },
        body: formData,
      })

      let data = null
      try {
        data = await response.json()
      } catch (parseError) {
        data = null
      }

      if (!response.ok) {
        const detail = data && data.detail ? data.detail : `Upload failed (${response.status})`
        setError(typeof detail === 'string' ? detail : JSON.stringify(detail))
        return
      }

      setResult(data)
    } catch (err) {
      setError(`Upload failed: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="sticky top-0 z-10 border-b" style={{ backgroundColor: 'rgb(181, 181, 182)' }}>
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
          <div className="text-2xl font-bold" style={{ color: 'rgb(127, 16, 132)' }}>EMI Admin Upload</div>
          <a
            href="/"
            className="px-4 py-2 font-medium rounded-xl border-2 transition-colors"
            style={{ backgroundColor: 'white', color: 'rgb(127, 16, 132)', borderColor: 'rgb(127, 16, 132)' }}
          >
            Back to Search
          </a>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-10">
        <div className="rounded-2xl bg-white p-6 shadow-sm border">
          <h2 className="text-lg font-semibold mb-4">Upload Excel</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Admin Token</label>
              <input
                type="password"
                value={token}
                onChange={e => setToken(e.target.value)}
                className="w-full rounded-xl border px-4 py-2"
                placeholder="Enter admin token"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Excel (.xlsx)</label>
              <input
                type="file"
                accept=".xlsx"
                onChange={e => setFile(e.target.files && e.target.files[0] ? e.target.files[0] : null)}
                className="w-full"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 font-medium rounded-xl border-2 transition-colors"
              style={{ backgroundColor: 'rgb(127, 16, 132)', color: 'white', borderColor: 'rgb(127, 16, 132)' }}
            >
              {loading ? 'Uploading...' : 'Upload'}
            </button>
          </form>

          {error && (
            <div className="mt-4 text-sm text-red-600">{error}</div>
          )}

          {result && (
            <div className="mt-6 space-y-2 text-sm">
              <div className="font-medium">Import Result</div>
              <div>File: {result.filename}</div>
              <div>Total Rows: {result.total_rows}</div>
              <div>Inserted: {result.inserted}</div>
              <div>Updated: {result.updated}</div>
              <div>Skipped: {result.skipped}</div>
              {result.errors && result.errors.length > 0 && (
                <div className="mt-2">
                  <div className="font-medium">Errors</div>
                  <ul className="list-disc pl-5">
                    {result.errors.map((err, i) => (
                      <li key={i}>{err.sheet} row {err.row}: {err.error}</li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="text-gray-600 mt-3">
                Upload completed. Please return to the search page and refresh to see the latest data.
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
