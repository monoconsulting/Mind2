import { api, renderShell } from '../wireframe.js'

export function renderExport() {
  renderShell(`
    <section>
      <h2>Export SIE</h2>
      <form id="exp" class="dm-card" style="display:flex;gap:.5rem;align-items:end;padding:1rem;flex-wrap:wrap;">
        <div style="display:flex;gap:.5rem;align-items:end;">
          <label>From <input id="exp-from" type="date" /></label>
          <label>To <input id="exp-to" type="date" /></label>
          <button type="submit" class="dm">Generate</button>
        </div>
        <div style="margin-left:auto;display:flex;gap:.5rem;">
          <button type="button" class="dm" id="exp-this-month">This Month</button>
          <button type="button" class="dm" id="exp-last-month">Last Month</button>
          <button type="button" class="dm" id="exp-ytd">YTD</button>
          <button type="button" class="dm" id="exp-year">This Year</button>
        </div>
      </form>
      <div class="text-dm-subt" id="exp-out"></div>
    </section>
  `);
  const form = document.getElementById('exp');
  const out = document.getElementById('exp-out');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    out.textContent = 'Generating...';
    const qs = new URLSearchParams();
    const f = document.getElementById('exp-from').value;
    const t = document.getElementById('exp-to').value;
    if (f) qs.set('from', f);
    if (t) qs.set('to', t);
    const res = await api.fetch(`/ai/api/export/sie?${qs.toString()}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const fname = makeFileName(f, t);
    a.href = url;
    a.download = fname;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    out.textContent = `${res.status}: Downloaded ${fname}`;
  });

  // Quick presets
  document.getElementById('exp-this-month').addEventListener('click', () => setRange(startOfThisMonth(), endOfThisMonth()))
  document.getElementById('exp-last-month').addEventListener('click', () => setRange(startOfLastMonth(), endOfLastMonth()))
  document.getElementById('exp-ytd').addEventListener('click', () => setRange(startOfYear(), today()))
  document.getElementById('exp-year').addEventListener('click', () => setRange(startOfYear(), endOfYear()))

  function setRange(from, to) {
    document.getElementById('exp-from').value = from;
    document.getElementById('exp-to').value = to;
  }

  function fmt(d) { return d.toISOString().slice(0,10) }
  function today() { return fmt(new Date()) }
  function startOfThisMonth() { const d=new Date(); return fmt(new Date(d.getFullYear(), d.getMonth(), 1)) }
  function endOfThisMonth() { const d=new Date(); return fmt(new Date(d.getFullYear(), d.getMonth()+1, 0)) }
  function startOfLastMonth() { const d=new Date(); return fmt(new Date(d.getFullYear(), d.getMonth()-1, 1)) }
  function endOfLastMonth() { const d=new Date(); return fmt(new Date(d.getFullYear(), d.getMonth(), 0)) }
  function startOfYear() { const d=new Date(); return fmt(new Date(d.getFullYear(), 0, 1)) }
  function endOfYear() { const d=new Date(); return fmt(new Date(d.getFullYear(), 11, 31)) }
  function makeFileName(f, t) { return `export_${(f||'start')}_${(t||'end')}.sie` }
}
