// Inject v2.22c-style staged entrance animation into the NEW b-step 1:1 HTML files.
// Robust generic version: header pieces staged at 0/1.5/3s, full body fades in at 4.5s.
const fs = require('fs');
const dir = __dirname + '/';

const ANIM = `<style data-purpose="round3-animations">
@keyframes fadeIn{ to{ opacity:1; } }
.chart-logo-1x1{ opacity:0; animation: fadeIn 1.2s ease-out 0s forwards; }
.chart-title-1x1{ opacity:0; animation: fadeIn 1.2s ease-out 1.5s forwards; }
.chart-source-1x1{ opacity:0; animation: fadeIn 1.2s ease-out 3s forwards; }
.chart-part-num{ opacity:0; animation: fadeIn 1.2s ease-out 3s forwards; }
.chart-body-1x1{ opacity:0; animation: fadeIn 1.5s ease-out 4.5s forwards; }
#yz-selfcheck-banner{ display:none !important; }
body{ background:#fff !important; padding:0 !important; margin:0 !important; }
</style>`;

const inputs = [
  'img3-part1-styled.html',
  'img3-part2-styled.html',
  'shenteng-part1-styled.html',
  'shenteng-part2-styled.html',
  'shenteng-part3-styled.html',
  'shenteng-part4-styled.html',
  'shenteng-part5-styled.html',
  'shenteng-part6-styled.html',
];

inputs.forEach(f => {
  const src = fs.readFileSync(dir + f, 'utf8');
  if (src.includes('round3-animations')) { console.log('skip (already animated): ' + f); return; }
  const outName = f.replace('-styled.html', '-anim.html');
  const out = src.replace('</head>', ANIM + '\n</head>');
  fs.writeFileSync(dir + outName, out);
  console.log('wrote ' + outName);
});
