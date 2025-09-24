import { api, navigate, renderShell } from '../wireframe.js'

export async function renderReceiptDetail(params = {}) {
  const id = params?.id
  if (!id) {
    return navigate('receipts')
  }

  renderShell(`
    <section class="dm-card" style="padding:1rem;">
      <div style="display:grid;grid-template-columns: 2fr 3fr; gap:1rem; align-items:start;">
        <div>
          <div class="dm-card" style="padding:0; overflow:hidden;">
            <div style="display:flex;justify-content:space-between;align-items:center;padding:.5rem 1rem;border-bottom:1px solid var(--dm-border);">
              <strong>Receipt #${id}</strong>
              <button class="dm" id="back">Back</button>
            </div>
            <div style="padding:0; background: var(--dm-bg); display:flex; justify-content:center; align-items:center; min-height:420px;">
              <img id="preview" alt="preview" style="max-width:100%; max-height:600px; display:none;" />
              <div id="noimg" class="text-dm-subt">No image available</div>
            </div>
          </div>
        </div>
        <div>
          <form id="frm" class="dm-card" style="padding:1rem; display:grid; grid-template-columns: 1fr 1fr; gap:.75rem;">
            <label style="display:flex; flex-direction:column; gap:.25rem;">Merchant
              <input id="merchant" type="text" />
            </label>
            <label style="display:flex; flex-direction:column; gap:.25rem;">Date
              <input id="purchase_date" type="date" />
            </label>
            <label style="display:flex; flex-direction:column; gap:.25rem;">Gross
              <input id="gross_amount" type="number" step="0.01" />
            </label>
            <label style="display:flex; flex-direction:column; gap:.25rem;">Net
              <input id="net_amount" type="number" step="0.01" />
            </label>
            <label style="display:flex; flex-direction:column; gap:.25rem;">VAT Amount
              <input id="vat_amount" type="number" step="0.01" />
            </label>
            <label style="display:flex; flex-direction:column; gap:.25rem;">VAT %
              <input id="vat_rate" type="number" step="0.1" />
            </label>
            <div style="grid-column: 1 / -1; display:flex; gap:.5rem; margin-top:.5rem;">
              <button type="submit" class="dm" id="save">Save</button>
              <button type="button" class="dm" id="approve">Approve</button>
              <span id="msg" class="text-dm-subt"></span>
            </div>
          </form>
          <div class="dm-surface" style="padding:1rem; margin-top:1rem; display:grid; grid-template-columns: 1fr 1fr; gap:1rem;">
            <div>
              <h3 class="text-lg">Validation</h3>
              <pre id="validation" class="text-sm text-dm-subt"></pre>
            </div>
            <div>
              <h3 class="text-lg">Proposed Accounting</h3>
              <pre id="accounting" class="text-sm text-dm-subt">Will appear when server support is wired</pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  `)

  document.getElementById('back').addEventListener('click', () => navigate('receipts'))

  // Load receipt data
  let data = null
  try {
    const res = await api.fetch(`/ai/api/receipts/${id}`)
    if (res.ok) {
      data = await res.json()
    }
  } catch {}

  // Populate form
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.value = v ?? '' }
  set('merchant', data?.merchant || data?.merchant_name)
  set('purchase_date', (data?.purchase_date || '').slice(0, 10))
  set('gross_amount', data?.gross_amount)
  set('net_amount', data?.net_amount)
  set('vat_amount', data?.vat_amount)
  set('vat_rate', data?.vat_rate)

  // Show status info
  const valEl = document.getElementById('validation')
  valEl.textContent = JSON.stringify({ status: data?.status || data?.ai_status, confidence: data?.confidence }, null, 2)

  // Try load preview image (best-effort)
  const img = document.getElementById('preview')
  const noimg = document.getElementById('noimg')
  try {
    img.src = `/ai/api/receipts/${id}/image`
    img.onerror = () => { img.style.display = 'none'; noimg.style.display = 'block' }
    img.onload = () => { noimg.style.display = 'none'; img.style.display = 'block' }
  } catch {}

  // Save handler
  const form = document.getElementById('frm')
  const msg = document.getElementById('msg')
  form.addEventListener('submit', async (e) => {
    e.preventDefault()
    msg.textContent = 'Saving...'
    const payload = {
      merchant: document.getElementById('merchant').value || null,
      purchase_date: document.getElementById('purchase_date').value || null,
      gross_amount: parseFloat(document.getElementById('gross_amount').value || '0'),
      net_amount: parseFloat(document.getElementById('net_amount').value || '0'),
      vat_amount: parseFloat(document.getElementById('vat_amount').value || '0'),
      vat_rate: parseFloat(document.getElementById('vat_rate').value || '0'),
    }
    try {
      const res = await api.fetch(`/ai/api/receipts/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      msg.textContent = res.ok ? 'Saved' : `Error ${res.status}`
    } catch (ex) {
      msg.textContent = String(ex)
    }
  })

  // Approve handler (best-effort)
  document.getElementById('approve').addEventListener('click', async () => {
    msg.textContent = 'Approving...'
    try {
      const res = await api.fetch(`/ai/api/receipts/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: 'completed' }) })
      msg.textContent = res.ok ? 'Approved' : `Error ${res.status}`
    } catch (ex) {
      msg.textContent = String(ex)
    }
  })
}
