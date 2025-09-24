import { api, navigate, register, renderShell } from './wireframe.js'

function renderDashboard() {
  renderShell(`
    <section>
      <p>Welcome to Mind Admin.</p>
      <button id="ping">Ping API</button>
      <pre id="out"></pre>
    </section>
  `);
  document.getElementById('ping').addEventListener('click', ping);
}
import { renderKvitton } from './views/receipts.js'
import { renderReceiptDetail } from './views/receipt_detail.js'
import { renderSettingsRules } from './views/settings_rules.js'
import { renderCompanyCard } from './views/company_card.js'
import { renderExport } from './views/export.js'
// --- actions ---
async function ping() {
  const out = document.getElementById('out');
  try {
    const res = await api.fetch('/ai/api/admin/ping');
    const txt = await res.text();
    out.textContent = `${res.status}: ${txt}`;
  } catch (e) {
    out.textContent = `Error: ${e}`;
  }
}
register('dashboard', renderDashboard)
register('receipts', renderKvitton)
register('export', renderExport)
register('receipt', renderReceiptDetail)
register('settings', renderSettingsRules)
register('company-card', renderCompanyCard)
// initial route
navigate(localStorage.getItem('mind.jwt') ? 'dashboard' : 'login')

