const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const html=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8');
const script=fs.readFileSync('newsmuncher/static/js/creation/script.js','utf8');
const sounds=fs.readFileSync('newsmuncher/static/js/creation/udder-sounds.js','utf8');

test('Create exposes three ordered engines and sends the selected engine once',()=>{
  for(const value of ['classic','current','experimental'])assert(html.includes(`('${value}',`));
  assert(html.indexOf("('classic',")<html.indexOf("('current',"));
  assert(html.indexOf("('current',")<html.indexOf("('experimental',"));
  assert.match(script,/const engine = event\?\.currentTarget\?\.dataset\?\.mungeEngine \|\| 'current'/);
  assert.match(script,/JSON\.stringify\(\{title,description,extract,draft_session:workingSession\(\),engine\}\)/);
  assert.match(script,/if \(mungeProcessing\) return/);
});

test('all three controls share processing, failure cleanup and one delegated sound',()=>{
  assert.match(script,/querySelectorAll\('\.munge-control'\)/);
  assert.match(script,/querySelectorAll\('\.munge-rotor'\)/);
  assert.match(script,/querySelectorAll\('\.munge-body-button'\)/);
  assert(!script.includes("querySelectorAll('.munge-body-button, .munge-teat').forEach(button => {\n            button.disabled = true"));
  assert.match(script,/\.catch\(error => \{[\s\S]*hideLoader\(\)/);
  assert.match(sounds,/mungeSoundTargets=Object\.freeze\(\{\.\.\.bodies\}\)/);
  assert.match(sounds,/teats:controls\.map/);
  assert.match(sounds,/clickSound:'assigned'/);
  assert.doesNotMatch(sounds,/bodies:Object\.fromEntries/);
  assert.doesNotMatch(sounds,/munge:button/);
});

test('soundtrack follows the single MUNGE request lifecycle without disabling teats',()=>{
  const confirm=script.slice(script.indexOf('function confirmData'),script.indexOf('let nominationPending'));
  assert.equal((confirm.match(/fetch\("\/temp\/shizzalise_data"/g)||[]).length,1);
  assert(confirm.indexOf('window.mungeMusic?.start(mungeClickedAt)')<confirm.indexOf('fetch("/temp/shizzalise_data"'));
  assert(confirm.indexOf('window.mungeMusic?.markApiDispatched()')<confirm.indexOf('fetch("/temp/shizzalise_data"'));
  assert.equal((confirm.match(/window\.mungeMusic\?\.stop\(\)/g)||[]).length,2);
  assert.match(script,/function beginNewCreation\(\) \{\s*window\.mungeMusic\?\.stop\(\)/);
  assert.match(script,/function cancelMungeProcessingImmediately\(\) \{\s*window\.mungeMusic\?\.stop\(\)/);
  assert(!script.includes("querySelectorAll('.munge-teat').forEach(button => {\n            button.disabled = true"));
});
