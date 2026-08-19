const form = document.getElementById('predictionForm');
const grid = document.getElementById('inputGrid');
const resultSection = document.getElementById('resultSection');
const errorBox = document.getElementById('errorBox');
const sample = {cement: 350, blast_furnace_slag: 100, fly_ash: 0, water: 180, superplasticizer: 8, coarse_aggregate: 1000, fine_aggregate: 750, age: 28};
let featureMeta = [];

const pretty = {cement:'Cement', blast_furnace_slag:'Blast furnace slag', fly_ash:'Fly ash', water:'Water', superplasticizer:'Superplasticizer', coarse_aggregate:'Coarse aggregate', fine_aggregate:'Fine aggregate', age:'Curing age'};
function showError(message){ errorBox.textContent = message; errorBox.hidden = false; }
function clearError(){ errorBox.hidden = true; errorBox.textContent = ''; }
function renderInputs(){
  grid.innerHTML = featureMeta.map((item) => `<div class="field"><label for="${item.key}">${item.label}<span>${item.key === 'age' ? 'days' : 'kg/m³'}</span></label><input id="${item.key}" name="${item.key}" type="number" min="0" step="any" required aria-label="${item.label}" /></div>`).join('');
  fillForm(sample);
}
function fillForm(values){ Object.entries(values).forEach(([key, value]) => { const input = document.getElementById(key); if(input) input.value = value; }); }
function formatTime(iso){ return new Date(iso).toLocaleString([], {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'}); }
async function loadDashboard(){
  try{
    const [metaRes, historyRes] = await Promise.all([fetch('/api/metadata'), fetch('/api/history')]);
    if(!metaRes.ok) throw new Error('Metadata unavailable');
    const meta = await metaRes.json(); featureMeta = meta.features; renderInputs();
    document.getElementById('datasetRows').textContent = meta.dataset_rows.toLocaleString();
    renderHistory((await historyRes.json()).items || []);
  }catch(error){ showError('The dashboard could not connect to the model service. Please start the API and try again.'); }
}
function renderHistory(items){
  const body = document.getElementById('historyBody');
  if(!items.length){ body.innerHTML = '<tr><td colspan="5" class="empty-state">No predictions yet. Your recent runs will appear here.</td></tr>'; return; }
  body.innerHTML = items.map((item, index) => `<tr><td>#${String(items.length-index).padStart(2,'0')}</td><td class="history-strength">${item.strength_mpa.toFixed(2)} MPa</td><td><span class="history-band">${item.band}</span></td><td>${item.inputs.age} days</td><td>${formatTime(item.created_at)}</td></tr>`).join('');
}
form.addEventListener('submit', async (event) => {
  event.preventDefault(); clearError();
  const button = form.querySelector('.primary-button'); button.disabled = true; button.querySelector('span:first-child').textContent = 'Calculating…';
  const values = Object.fromEntries(new FormData(form).entries());
  Object.keys(values).forEach(key => values[key] = Number(values[key]));
  try{
    const response = await fetch('/api/predict', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(values)});
    const data = await response.json();
    if(!response.ok) throw new Error(data.detail || 'Please check the input values.');
    document.getElementById('strengthValue').textContent = data.strength_mpa.toFixed(2);
    document.getElementById('bandBadge').textContent = data.band;
    document.getElementById('interpretationText').textContent = data.interpretation;
    document.getElementById('resultTime').textContent = formatTime(data.created_at);
    resultSection.hidden = false; resultSection.scrollIntoView({behavior:'smooth', block:'start'});
    renderHistory((await (await fetch('/api/history')).json()).items || []);
  }catch(error){ showError(error.message || 'We could not complete that prediction. Please try again.'); }
  finally{ button.disabled = false; button.querySelector('span:first-child').textContent = 'Run prediction'; }
});
document.getElementById('sampleBtn').addEventListener('click', () => { fillForm(sample); clearError(); });
document.getElementById('refreshBtn').addEventListener('click', () => { loadDashboard(); });
loadDashboard();
