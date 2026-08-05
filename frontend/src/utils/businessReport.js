// Builds a self-contained, printable business-plan document from an estimate response.

export const inr = (n) => '₹' + Number(n || 0).toLocaleString('en-IN');

function rows(items) {
  return items
    .map(
      (x) => `<tr><td>${x.item}</td><td class="amt">${inr(x.amount)}</td>
              <td class="note">${x.note || ''}</td></tr>`
    )
    .join('');
}

export function buildReportHTML(est) {
  const t = est.totals;
  const staff = (est.staff || [])
    .map((s) => `${s.count}× ${s.role} @ ${inr(s.monthly_salary)}/mo`)
    .join(', ');
  const assumptions = (est.assumptions || []).map((a) => `<li>${a}</li>`).join('');

  return `<!doctype html><html><head><meta charset="utf-8">
<title>Business Plan — ${est.business_type}</title>
<style>
  *{box-sizing:border-box} body{font:14px/1.5 'Segoe UI',system-ui,sans-serif;color:#2a2420;margin:0;padding:40px;max-width:820px;margin:auto}
  h1{font-size:26px;margin:0 0 4px;color:#c2652a} h2{font-size:16px;margin:28px 0 8px;border-bottom:2px solid #eee;padding-bottom:4px}
  .sub{color:#777;margin-bottom:18px}
  .cards{display:flex;gap:12px;margin:16px 0}
  .card{flex:1;border:1px solid #eadfd3;border-radius:10px;padding:12px;background:#faf5ee}
  .card .k{font-size:11px;text-transform:uppercase;color:#8a7d6d;letter-spacing:.04em}
  .card .v{font-size:20px;font-weight:700;color:#2a2420;margin-top:4px}
  table{width:100%;border-collapse:collapse;margin-top:6px} td{padding:6px 8px;border-bottom:1px solid #f0eae0}
  .amt{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap} .note{color:#999;font-size:12px}
  tfoot td{font-weight:700;border-top:2px solid #ddd}
  .disc{margin-top:24px;font-size:12px;color:#999;border-top:1px solid #eee;padding-top:10px}
  @media print{body{padding:0}}
</style></head><body>
  <h1>Business Plan — ${est.business_type}</h1>
  <div class="sub">${est.size_sqft} sqft · ${est.tier} tier · Mumbai
     · location ${est.location.lat.toFixed(4)}, ${est.location.lng.toFixed(4)}</div>

  <div class="cards">
    <div class="card"><div class="k">One-time setup</div><div class="v">${inr(t.one_time)}</div></div>
    <div class="card"><div class="k">Monthly running</div><div class="v">${inr(t.monthly)}</div></div>
    <div class="card"><div class="k">Total to start*</div><div class="v">${inr(t.startup_total)}</div></div>
  </div>

  <p>${est.summary || ''}</p>

  <h2>One-time (capital) costs</h2>
  <table>${rows(est.one_time)}
    <tfoot><tr><td>Total one-time</td><td class="amt">${inr(t.one_time)}</td><td></td></tr></tfoot></table>

  <h2>Monthly (operating) costs</h2>
  <table>${rows(est.monthly)}
    <tfoot><tr><td>Total monthly</td><td class="amt">${inr(t.monthly)}</td><td></td></tr></tfoot></table>
  ${staff ? `<p class="note">Staffing: ${staff}</p>` : ''}

  <h2>To start you need</h2>
  <table>
    <tr><td>One-time setup</td><td class="amt">${inr(t.one_time)}</td><td class="note"></td></tr>
    <tr><td>Working capital (${t.working_capital_months} months of running cost)</td>
        <td class="amt">${inr(t.working_capital)}</td><td class="note">buffer before break-even</td></tr>
    <tfoot><tr><td>Total capital to start</td><td class="amt">${inr(t.startup_total)}</td><td></td></tr></tfoot>
  </table>

  ${assumptions ? `<h2>Assumptions</h2><ul>${assumptions}</ul>` : ''}
  <div class="disc">Rent basis: ${est.rent_basis}.<br>${est.disclaimer}</div>
</body></html>`;
}

// Opens the report in a new window and triggers the print/save-as-PDF dialog.
export function openPlanReport(est) {
  const html = buildReportHTML(est);
  const w = window.open('', '_blank');
  if (!w) return;
  w.document.write(html);
  w.document.close();
  w.focus();
  setTimeout(() => w.print(), 400);
}

// Also offer a raw .html download.
export function downloadPlanHTML(est) {
  const blob = new Blob([buildReportHTML(est)], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `business-plan-${est.business_type.replace(/\s+/g, '-')}.html`;
  a.click();
  URL.revokeObjectURL(url);
}
