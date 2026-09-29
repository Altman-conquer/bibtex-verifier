const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../docs/index.html'), 'utf8');
const code = html.split('<script>')[1].split('</script>')[0];
const fake = { addEventListener(event, callback) { (this.listeners ||= {})[event] = callback; }, appendChild() {}, replaceChildren() {}, classList: { add() {}, remove() {} }, dataset: {}, style: {}, value: '82' };
const ids = new Map();
const ctx = vm.createContext({
  document: { getElementById: id => { if (!ids.has(id)) ids.set(id, { ...fake }); return ids.get(id); }, querySelectorAll: () => [], documentElement: {},
    createElement: () => ({ ...fake, innerHTML: '' }) },
  URLSearchParams, AbortController, setTimeout, clearTimeout,
  fetch: async () => ({ status: 429, ok: false })
});
vm.runInContext(code, ctx);
const bib = '@comment{ignored}\n@string{jan = \"January\"}\n@article{gaia, title={A {B {C}} @symbol}, author={Gr{\\\'{e}}goire Mialon and Other Author}, year={2024}}\n@article{next, title={Next}}';
assert.equal(ctx.parseBib(bib).length, 2);
ctx.document.getElementById('bib-paste').value = bib;
ids.get('paste-btn').listeners.click();
assert.equal(vm.runInContext('parsedEntries.length', ctx), 2);
assert.equal(vm.runInContext('currentBibName', ctx), 'pasted');
assert.equal(ids.get('verify-btn').disabled, false);
assert.match(ctx.parseBib(bib)[0].author, /Mialon/);
assert.equal(ctx.firstAuthorLastname(ctx.parseBib(bib)[0].author), 'mialon');
assert.equal(ctx.firstAuthorLastname('Cheng, Yuxing'), 'cheng');
const evil = '<img src=x onerror=alert(1)>';
const card = ctx.renderCard({ key: evil, bibTitle: evil, status: 'OK', source: 'crossref', matchScore: 99,
  apiData: { title: evil, year: 2025, authors: [evil], venue: evil },
  issues: [{key: 'issueTitleMismatch', args: [33, evil, evil]}] });
assert(!card.innerHTML.includes('<img'));
assert(card.innerHTML.includes('&lt;img'));
(async () => {
  await assert.rejects(ctx.oaSearch('Real Paper', ''), /HTTP 429/);
  let attempts = 0;
  ctx.fetch = async () => {
    attempts++;
    return attempts === 1 ? { status: 503, ok: false } : { status: 200, ok: true, json: async () => ({ recovered: true }) };
  };
  assert.equal((await ctx.getJson('https://example.test')).recovered, true);
  assert.equal(attempts, 2);
  ctx.fetch = async url => {
    assert.equal(new URL(url).searchParams.get('search'), 'reasoning or memorization');
    return { status: 200, ok: true, json: async () => ({ results: [] }) };
  };
  assert.equal(await ctx.oaSearch('Reasoning or memorization?', ''), null);
  ctx.fetch = async () => ({ status: 429, ok: false });
  await ctx.verifyAll([{ ID: 'real', title: 'Real Paper' }]);
  assert.equal(vm.runInContext('allResults[0].status', ctx), 'UNVERIFIED');
  assert.match(ctx.buildMarkdown(vm.runInContext('allResults', ctx)), /HTTP 429/);
  ctx.fetch = async () => ({ status: 200, ok: true, json: async () => ({data: {attributes: {titles: [{title: 'Qwen3 Technical Report'}]}}}) });
  assert.equal((await ctx.dataciteByDoi('10.48550/arxiv.2505.09388')).titles[0].title, 'Qwen3 Technical Report');
  const sample = path.join(__dirname, '../marketing/iclr-demo');
  if (fs.existsSync(sample)) for (const name of ['arpo', 'beyondbench', 'learn-to-distance']) {
    assert.equal(ctx.parseBib(fs.readFileSync(path.join(sample, `${name}.bib`), 'utf8')).length, 12, name);
  }
  console.log('web smoke: parser, author names, HTML escaping, API 429 passed');
})().catch(err => { console.error(err); process.exitCode = 1; });
