import { api, renderShell } from '../wireframe.js'

export async function renderSettingsRules() {
  renderShell(`
    <section>
      <h2>Accounting Rules</h2>
      <form id="new" class="dm-card" style="padding:1rem; display:flex; gap:.5rem; align-items:end;">
        <label>Matcher <input id="n-matcher" placeholder="merchant contains..." /></label>
        <label>Account <input id="n-account" placeholder="e.g. 5610" /></label>
        <label>Note <input id="n-note" placeholder="optional" /></label>
        <button type="submit" class="dm">Add</button>
      </form>
      <table id="tbl" style="width:100%; border-collapse:collapse; margin-top:.5rem;">
        <thead><tr><th style="text-align:left;">Matcher</th><th style="text-align:left;">Account</th><th style="text-align:left;">Note</th><th></th></tr></thead>
        <tbody></tbody>
      </table>
    </section>
  `)

  async function load() {
    const tbody = document.querySelector('#tbl tbody')
    tbody.innerHTML = '<tr><td colspan="4" class="text-dm-subt">Loading...</td></tr>'
    const res = await api.fetch('/ai/api/rules')
    const items = res.ok ? await res.json() : []
    tbody.innerHTML = ''
    for (const r of items) {
      const tr = document.createElement('tr')
      tr.innerHTML = `
  <td style="padding:.25rem .5rem;border-top:1px solid var(--dm-border);"><input class="dm-input" data-k="matcher" value="${r.matcher ?? ''}" /></td>
  <td style="padding:.25rem .5rem;border-top:1px solid var(--dm-border);"><input class="dm-input" data-k="account" value="${r.account ?? ''}" /></td>
  <td style="padding:.25rem .5rem;border-top:1px solid var(--dm-border);"><input class="dm-input" data-k="note" value="${r.note ?? ''}" /></td>
        <td style="padding:.25rem .5rem;border-top:1px solid var(--dm-border); text-align:right;">
          <button class="dm" data-act="save" data-id="${r.id}">Save</button>
          <button class="dm" data-act="del" data-id="${r.id}">Delete</button>
        </td>
      `
      tbody.appendChild(tr)
    }
    tbody.querySelectorAll('button[data-act]')?.forEach(btn => btn.addEventListener('click', async (e) => {
      const id = e.currentTarget.getAttribute('data-id')
      const act = e.currentTarget.getAttribute('data-act')
      const row = e.currentTarget.closest('tr')
      if (act === 'save') {
        const payload = {
          matcher: row.querySelector('input[data-k="matcher"]').value,
          account: row.querySelector('input[data-k="account"]').value,
          note: row.querySelector('input[data-k="note"]').value,
        }
        await api.fetch(`/ai/api/rules/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      } else if (act === 'del') {
        await api.fetch(`/ai/api/rules/${id}`, { method: 'DELETE' })
      }
      await load()
    }))
  }

  document.getElementById('new').addEventListener('submit', async (e) => {
    e.preventDefault()
    const matcher = document.getElementById('n-matcher').value
    const account = document.getElementById('n-account').value
    const note = document.getElementById('n-note').value
    await api.fetch('/ai/api/rules', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ matcher, account, note }) })
    e.target.reset()
    await load()
  })

  await load()
}
