// Kvitton Dashboard view (filters + sorting + pagination)
import { api, navigate, renderShell } from '../wireframe.js'

const renderStatusBadge = (status) => {
  const s = (status || 'new').toLowerCase();
  const colors = {
    new: '#3b82f6',
    completed: '#22c55e',
    failed: '#ef4444',
    error: '#ef4444',
    manual_review: '#f59f00',
    processing: '#6366f1',
    ocr_done: '#6366f1',
    classified_receipt: '#6366f1',
    accounting_proposed: '#a855f7',
  };
  const color = colors[s] || '#6b7280';
  return `<span style="background-color:${color}; color:white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; text-transform: capitalize;">${s.replace(/_/g, ' ')}</span>`;
};

const openImageModal = (receiptId) => {
  const modal = document.getElementById('image-modal');
  const modalImg = document.getElementById('modal-image');
  if (modal && modalImg) {
    modalImg.src = `/ai/api/receipts/${receiptId}/image`;
    modal.style.display = 'flex';
  }
};

const closeImageModal = () => {
  const modal = document.getElementById('image-modal');
  if (modal) {
    modal.style.display = 'none';
  }
};

export function renderKvitton() {
  renderShell(`
    <div id="image-modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.7); align-items:center; justify-content:center; z-index:1000;">
      <img id="modal-image" style="max-width:90vw; max-height:90vh;" />
      <button id="modal-close" style="position:absolute; top:20px; right:20px; color:white; font-size:2rem; background:transparent; border:none; cursor:pointer;">&times;</button>
    </div>
    <section>
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h2>Kvitton</h2>
        <button id="fetch-ftp" class="dm">Hämta kvitton</button>
      </div>
      <form id="filters" class="dm-card" style="display:grid;grid-template-columns:repeat(6,1fr);gap:.5rem;align-items:end;padding:1rem;margin-bottom:.5rem;">
        <label style="display:flex;flex-direction:column;gap:.25rem;">Status
          <select id="f-status">
            <option value="">(any)</option>
            <option value="new">New</option>
            <option value="processing">Processing</option>
            <option value="passed">Passed</option>
            <option value="failed">Failed</option>
            <option value="manual_review">Needs Review</option>
            <option value="completed">Completed</option>
          </select>
        </label>
        <label style="display:flex;flex-direction:column;gap:.25rem;">Merchant
          <input id="f-merchant" placeholder="Search merchant" />
        </label>
        <label style="display:flex;flex-direction:column;gap:.25rem;">Tags
          <input id="f-tags" placeholder="comma,separated" />
        </label>
        <label style="display:flex;flex-direction:column;gap:.25rem;">From
          <input id="f-from" type="date" />
        </label>
        <label style="display:flex;flex-direction:column;gap:.25rem;">To
          <input id="f-to" type="date" />
        </label>
        <div style="display:flex;gap:.5rem;">
          <button id="apply" type="submit">Apply</button>
          <button id="reset" type="button">Reset</button>
        </div>
      </form>
      <div style="display:flex;align-items:center;gap:.5rem;margin:.25rem 0;">
        <div id="status"></div>
        <div style="margin-left:auto;display:flex;gap:.25rem;align-items:center;">
          <label>Page size
            <select id="page-size">
              <option>10</option>
              <option selected>50</option>
              <option>100</option>
            </select>
          </label>
          <button id="prev">Prev</button>
          <span id="page-info"></span>
          <button id="next">Next</button>
        </div>
      </div>
  <table id="tbl" style="width:100%;border-collapse:collapse;margin-top:.5rem;">
        <thead>
          <tr>
            <th data-sort="original_filename" style="text-align:left;cursor:pointer;">Filename</th>
            <th data-sort="merchant" style="text-align:left;cursor:pointer;">Merchant</th>
            <th data-sort="gross_amount" style="text-align:right;cursor:pointer;">Gross</th>
            <th data-sort="status" style="text-align:left;cursor:pointer;">Status</th>
            <th style="text-align:right;">Action</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </section>
  `)

  const state = { page: 1 }
  const form = document.getElementById('filters')
  const resetBtn = document.getElementById('reset')
  const prevBtn = document.getElementById('prev')
  const nextBtn = document.getElementById('next')
  const pageSizeSel = document.getElementById('page-size')
  const pageInfo = document.getElementById('page-info')
  const thead = document.querySelector('#tbl thead')
  const fetchFtpBtn = document.getElementById('fetch-ftp');

  document.getElementById('modal-close').addEventListener('click', closeImageModal);
  document.getElementById('image-modal').addEventListener('click', (e) => {
    if (e.target.id === 'image-modal') {
      closeImageModal();
    }
  });

  fetchFtpBtn.addEventListener('click', async () => {
    const statusEl = document.getElementById('status');
    statusEl.textContent = 'Fetching from FTP...';
    fetchFtpBtn.disabled = true;
    try {
      const res = await api.fetch('/ai/api/ingest/fetch-ftp', { method: 'POST' });
      if (!res.ok) throw new Error(`FTP Fetch failed: ${res.status}`);
      const result = await res.json();
      statusEl.textContent = `Fetched ${result.downloaded?.length || 0} new files.`;
      loadKvitton(state);
    } catch (e) {
      statusEl.textContent = `Error: ${e.message}`;
    } finally {
      fetchFtpBtn.disabled = false;
    }
  });

  let sort = { key: 'created_at', dir: 'desc' }

  thead.addEventListener('click', (e) => {
    const th = e.target.closest('th')
    if (!th) return
    const key = th.getAttribute('data-sort')
    if (!key) return
    if (sort.key === key) {
      sort.dir = sort.dir === 'asc' ? 'desc' : 'asc'
    } else {
      sort = { key, dir: 'asc' }
    }
    loadKvitton(state)
  })

  form.addEventListener('submit', (e) => { e.preventDefault(); state.page = 1; loadKvitton(state) })
  resetBtn.addEventListener('click', () => { form.reset(); state.page = 1; loadKvitton(state) })
  prevBtn.addEventListener('click', () => { if (state.page > 1) { state.page -= 1; loadKvitton(state) } })
  nextBtn.addEventListener('click', () => { state.page += 1; loadKvitton(state) })
  pageSizeSel.addEventListener('change', () => { state.page = 1; loadKvitton(state) })

  async function loadKvitton(local) {
    const statusEl = document.getElementById('status')
    const tbody = document.querySelector('#tbl tbody')
    statusEl.textContent = 'Loading...'
    tbody.innerHTML = ''
    const qs = new URLSearchParams()
    const v = (id) => document.getElementById(id)?.value?.trim()
    const status = v('f-status'); if (status) qs.set('status', status)
    const merchant = v('f-merchant'); if (merchant) qs.set('merchant', merchant)
    const tags = v('f-tags'); if (tags) qs.set('tags', tags)
    const from = v('f-from'); if (from) qs.set('from', from)
    const to = v('f-to'); if (to) qs.set('to', to)
    const pageSize = parseInt(pageSizeSel.value || '50', 10)
    qs.set('page_size', String(Math.min(Math.max(pageSize, 1), 100)))
    qs.set('page', String(local?.page || 1))
    try {
      const res = await api.fetch(`/ai/api/receipts?${qs.toString()}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      let items = Array.isArray(data?.items) ? data.items : (Array.isArray(data) ? data : [])
      const meta = data?.meta || { page: local?.page || 1, page_size: pageSize, total: items.length }
      state.page = meta.page || local?.page || 1
      statusEl.textContent = `Loaded ${items.length} of ${meta.total} (page ${state.page})`
      pageInfo.textContent = `Page ${state.page}`
      prevBtn.disabled = state.page <= 1
      nextBtn.disabled = (state.page * pageSize) >= (meta.total || 0)

      // client-side sorting for current page
      const sorters = {
        original_filename: (a, b) => (a.original_filename || '').localeCompare(b.original_filename || ''),
        merchant: (a, b) => (a.merchant || a.merchant_name || '').localeCompare(b.merchant || b.merchant_name || ''),
        gross_amount: (a, b) => (a.gross_amount || 0) - (b.gross_amount || 0),
        status: (a, b) => (a.status || a.ai_status || '').localeCompare(b.status || b.ai_status || ''),
      }
      if (sort.key && sorters[sort.key]) {
        items.sort(sorters[sort.key])
        if (sort.dir === 'desc') items.reverse()
      }

      for (const r of items) {
        const tr = document.createElement('tr')
        tr.innerHTML = `
          <td style="padding:.25rem .5rem;border-top:1px solid var(--dm-border);"><a href="#" class="modal-link" data-id="${r.id}">${r.original_filename || r.id}</a></td>
          <td style="padding:.25rem .5rem;border-top:1px solid var(--dm-border);">${r.merchant ?? r.merchant_name ?? ''}</td>
          <td style="padding:.25rem .5rem;border-top:1px solid var(--dm-border);text-align:right;">${r.gross_amount ?? ''}</td>
          <td style="padding:.25rem .5rem;border-top:1px solid var(--dm-border);">${renderStatusBadge(r.status ?? r.ai_status)}</td>
          <td style="padding:.25rem .5rem;border-top:1px solid var(--dm-border);text-align:right;">
            <button class="dm view-btn" data-id="${r.id}">View</button>
          </td>
        `
        tbody.appendChild(tr)
      }
      tbody.querySelectorAll('.view-btn')?.forEach(btn => btn.addEventListener('click', (e) => {
        const id = e.currentTarget.getAttribute('data-id')
        navigate('receipt', { id })
      }))
      tbody.querySelectorAll('.modal-link')?.forEach(link => link.addEventListener('click', (e) => {
        e.preventDefault();
        const id = e.currentTarget.getAttribute('data-id');
        openImageModal(id);
      }));
    } catch (e) {
      statusEl.textContent = `Error: ${e}`
    }
  }

  loadKvitton(state)
}
