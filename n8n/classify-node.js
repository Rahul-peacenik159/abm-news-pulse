// Event types on headlines (subset of config/events.yaml). One signal per type per account.
const EVENTS = {
  funding: [/\b(raises?|raised|funding|series [a-h]\b|seed round|valuation)\b/i, 20, 'growth_budget_window'],
  acquisition: [/\b(acquires?|acquired|acquisition|merger|to buy|takeover)\b/i, 25, 'post_merger_integration'],
  leadership: [/\b(appoints?|appointed|names? new|hires?|new (ceo|cfo|cto|cmo|cro|ciso)|steps down|resigns?)\b/i, 20, 'new_leader_first_90_days'],
  expansion: [/\b(expands?|expansion|opens?|new (office|headquarters|hub|location))\b/i, 15, 'expansion_support'],
  layoffs: [/\b(layoffs?|lays off|job cuts|restructur\w*)\b/i, 15, 'cost_reduction_pitch'],
  security_incident: [/\b(breach|ransomware|cyberattack|hacked|data leak)\b/i, 15, 'incident_response_support'],
  partnership: [/\b(partners? with|partnership|teams up)\b/i, 10, 'partner_co_sell'],
};
const now = new Date().toISOString();
const accounts = $('Accounts').all();
const resp = $('GDELT articles').all();
const out = [];
accounts.forEach((acc, i) => {
  const name = acc.json.company.toLowerCase();
  const arts = (((resp[i] || {}).json || {}).articles || []).filter((a) => (a.title || '').toLowerCase().includes(name));
  for (const [type, [rx, weight, play]] of Object.entries(EVENTS)) {
    const hits = arts.filter((a) => rx.test(a.title || ''));
    if (!hits.length) continue;
    out.push({ account_domain: acc.json.domain, signal_type: 'news_' + type, signal_value: String(hits.length),
      tool_name: acc.json.company, category: 'news', role: 'trigger', weight, play, source: hits[0].domain,
      evidence: hits[0].title, evidence_url: hits[0].url, pack: 'news-pulse', observed_at: now });
  }
});
return out.map((json) => ({ json }));
