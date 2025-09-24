import { api, renderShell } from '../wireframe.js'

export async function renderCompanyCard() {
  renderShell(`
    <section>
      <h2>Company Card</h2>
      <div class="dm-card" style="padding:1rem; display:flex; gap:.75rem; align-items:end;">
        <label>Statement JSON <input id="fc-file" type="file" accept="application/json" /></label>
        <button id="fc-upload" class="dm">Import</button>
        <span id="fc-msg" class="text-dm-subt"></span>
      </div>
      <div class="dm-surface" style="padding:1rem; margin-top:.75rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <h3>Statements</h3>
          <button id="fc-refresh" class="dm">Refresh</button>
        </div>
        <table id="fc-tbl" style="width:100%; border-collapse: collapse; margin-top:.5rem;">
          <thead><tr><th style="text-align:left;">ID</th><th style="text-align:left;">File ID</th><th style="text-align:left;">Created</th><th style="text-align:right;">Actions</th></tr></thead>
          <tbody></tbody>
        </table>
      </div>
    </section>
  `)

  const msg = document.getElementById('fc-msg')

  document.getElementById('fc-upload').addEventListener('click', async () => {
    msg.textContent = 'Importing...'
    try {
      // For now we just POST an empty import or with a fake file_id; backend queues it
      const fileInput = document.getElementById('fc-file')
      let file_id = undefined
      if (fileInput.files && fileInput.files[0]) {
        // read a tiny piece to get a stable id; in real impl, upload to backend
        const content = await fileInput.files[0].text()
        file_id = `local-${Math.abs(hashCode(content))}`
      }
      const res = await api.fetch('/ai/api/reconciliation/firstcard/import', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ file_id }) })
      msg.textContent = res.ok ? 'Imported' : `Error ${res.status}`
      await load()
    } catch (e) {
      msg.textContent = String(e)
    }
  })

  document.getElementById('fc-refresh').addEventListener('click', load)

  async function load() {
    const tbody = document.querySelector('#fc-tbl tbody')
    tbody.innerHTML = '<tr><td colspan="4" class="text-dm-subt">Loading...</td></tr>'
    const res = await api.fetch('/ai/api/reconciliation/firstcard/statements')
    const data = res.ok ? await res.json() : { items: [] }
    tbody.innerHTML = ''
    for (const s of data.items || []) {
      const tr = document.createElement('tr')
      tr.innerHTML = `
  <td style="padding:.25rem .5rem;border-top:1px solid var(--dm-border);">${s.id}</td>
  <td style="padding:.25rem .5rem;border-top:1px solid var(--dm-border);">${s.file_id}</td>
  <td style="padding:.25rem .5rem;border-top:1px solid var(--dm-border);">${s.created_at}</td>
  <td style="padding:.25rem .5rem;border-top:1px solid var(--dm-border); text-align:right;">
          <button class="dm" data-act="match" data-id="${s.id}" data-file="${s.file_id}">Auto-match</button>
          <button class="dm" data-act="confirm" data-id="${s.id}">Confirm</button>
          <button class="dm" data-act="reject" data-id="${s.id}">Reject</button>
        </td>
      `
      tbody.appendChild(tr)
    }
    tbody.querySelectorAll('button[data-act]')?.forEach(btn => btn.addEventListener('click', onRowAction))
  }

  async function onRowAction(e) {
    const act = e.currentTarget.getAttribute('data-act')
    const id = e.currentTarget.getAttribute('data-id')
    if (!id) return
    let url = ''
    let method = 'POST'
    let body = undefined
    if (act === 'match') {
      url = '/ai/api/reconciliation/firstcard/match'
      body = JSON.stringify({ file_id: e.currentTarget.getAttribute('data-file') })
    } else if (act === 'confirm') {
      url = `/ai/api/reconciliation/firstcard/statements/${id}/confirm`
    } else if (act === 'reject') {
      url = `/ai/api/reconciliation/firstcard/statements/${id}/reject`
    }
    const headers = body ? { 'Content-Type': 'application/json' } : undefined
    const res = await api.fetch(url, { method, headers, body })
    msg.textContent = res.ok ? `${act} ok` : `${act} error ${res.status}`
    await load()
  }

  function hashCode(str) {
    let h = 0
    for (let i = 0; i < str.length; i++) { h = (h << 5) - h + str.charCodeAt(i); h |= 0 }
    return h
  }

  await load()
}
