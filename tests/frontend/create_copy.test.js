const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8');
const script=fs.readFileSync('newsmuncher/static/js/creation/script.js','utf8');
const css=fs.readFileSync('newsmuncher/static/css/shared/styles.css','utf8');
const base=fs.readFileSync('newsmuncher/templates/base.html','utf8');

test('Create result copy uses current editable text and reports success',async()=>{
  const body={value:''},button={hidden:true,disabled:true,textContent:'COPY'};
  const writes=[];
  const context={navigator:{clipboard:{writeText:async value=>writes.push(value)}},document:{getElementById:id=>id==='copyMungeButton'?button:body},setTimeout:()=>1,clearTimeout(){}};
  const functions=script.slice(script.indexOf('let copyFeedbackTimer'),script.indexOf('function autoResize'));
  vm.createContext(context);vm.runInContext(functions,context);
  context.updateCopyButton();assert.equal(button.hidden,true);
  body.value='Freshly generated text';context.updateCopyButton();assert.equal(button.hidden,false);
  body.value='Unsaved edited text';await context.copyMungeResult();
  assert.deepEqual(writes,['Unsaved edited text']);assert.equal(button.textContent,'COPIED!');
});

test('copy button shares the centred action row and does not narrow the editor',()=>{
  assert.match(html,/id="copyMungeButton"/);
  assert.match(html,/oninput="[^"]*updateCopyButton\(\)/);
  const actions=html.slice(html.indexOf('id="creationActions"'),html.indexOf('<!-- Operational status'));
  assert(actions.indexOf('id="copyMungeButton"') < actions.indexOf('id="bankButton"'));
  assert(actions.indexOf('id="bankButton"') < actions.indexOf('id="deleteCreationButton"'));
  assert.match(css,/#responseEditor\s*\{[^}]*padding:[^;}]* 0 0/s);
  assert.doesNotMatch(css,/#responseEditor\s*\{[^}]*padding-right/s);
  assert.doesNotMatch(css,/\.profile-page \.result-copy-button\s*\{/);
});

test('fresh Create assets expose a fully interactive inline result editor',()=>{
  const textarea=html.match(/<textarea id="responseBodyDraft"[^>]*>/)?.[0] || '';
  assert(textarea);assert.doesNotMatch(textarea,/\b(?:readonly|disabled)\b/i);
  assert.match(css,/#responseBodyDraft\s*\{[^}]*pointer-events:\s*auto[^}]*cursor:\s*text/s);
  assert.match(base,/styles\.css'\) \}\}\?v=create-actions-2/);
  assert.match(html,/script\.js'\) \}\}\?v=create-actions-4/);
});

test('nomination remains visible as NOMINATED and becomes editable only after changes',()=>{
  assert.match(script,/creationNominated\s*\?\s*\(changed\s*\?\s*'UPDATE NOMINATION'\s*:\s*'NOMINATED'\)/s);
  assert.match(script,/button\.disabled\s*=\s*nominationPending\s*\|\|\s*imageRedoPending\s*\|\|[\s\S]*creationNominated\s*&&\s*!changed/);
  const success=script.slice(script.indexOf('function bankThisBeauty'),script.indexOf('function setImageStyle'));
  assert.doesNotMatch(success,/bankButton'\)\.hidden\s*=\s*true/);
  assert.match(success,/renderNominationButton\(\)/);
  const restoreStart=script.indexOf('async function restoreImageRewrite');
  const restore=script.slice(restoreStart,script.indexOf("document.getElementById('mungeControls')",restoreStart));
  assert.match(restore,/extract\.value=data\.crazyReplacement1Extract\|\|'';\s*renderNominationButton\(\)/);
});

test('persisted nomination disables the button until the result is edited',()=>{
  const button={hidden:true,disabled:false,textContent:''};
  const body={value:'Saved article'},title={value:'Saved title'};
  const context={document:{getElementById:id=>id==='bankButton'?button:id==='responseTitleDraft'?title:body}};
  const functions=script.slice(script.indexOf('function responseEdited'),script.indexOf('let copyFeedbackTimer'));
  vm.createContext(context);
  vm.runInContext(`
    let displayedRewriteId='saved', creationNominated=true, nominationPending=false,
        imageRedoPending=false,
        nominatedSnapshot=JSON.stringify({crazyReplacement1Title:'Saved title',crazyReplacement1Extract:'Saved article'});
    function currentResultText(){return {crazyReplacement1Title:document.getElementById('responseTitleDraft').value,crazyReplacement1Extract:document.getElementById('responseBodyDraft').value};}
    ${functions}
  `,context);
  context.renderNominationButton();
  assert.equal(button.textContent,'NOMINATED');assert.equal(button.disabled,true);assert.equal(button.hidden,false);
  body.value='Unsaved edited article';context.responseEdited();
  assert.equal(button.textContent,'UPDATE NOMINATION');assert.equal(button.disabled,false);
});

test('pending or failed nomination keeps its label and restores retry access',()=>{
  const button={hidden:true,disabled:false,textContent:''},body={value:'Draft'},title={value:'Title'};
  const context={document:{getElementById:id=>id==='bankButton'?button:id==='responseTitleDraft'?title:body}};
  const functions=script.slice(script.indexOf('function responseEdited'),script.indexOf('let copyFeedbackTimer'));
  vm.createContext(context);vm.runInContext(`
    let displayedRewriteId='draft', creationNominated=false, nominationPending=true,
        imageRedoPending=false, nominatedSnapshot=null;
    function currentResultText(){return {crazyReplacement1Title:'Title',crazyReplacement1Extract:'Draft'};}
    ${functions}
  `,context);
  context.renderNominationButton();assert.equal(button.textContent,'NOMINATE');assert.equal(button.disabled,true);
  vm.runInContext('nominationPending=false',context);context.renderNominationButton();
  assert.equal(button.textContent,'NOMINATE');assert.equal(button.disabled,false);assert.equal(button.hidden,false);
});

test('MUNGE processing keeps rotor spin without scaling the control',()=>{
  assert.match(script,/rotors\.map\(rotor => rotor\.animate/);
  assert(!script.includes("transform:'scale(1.5)'"));
  assert(!css.includes('munge-control-processing-pulse'));
});

test('transparent MUNGE layers pass through while visible controls remain clickable',()=>{
  assert.match(css,/--munge-control-width:\s*min\(82vw, 370px\)/);
  assert.match(css,/\.profile-page \.profile-container\s*\{[^}]*margin-bottom:\s*calc\(2 \* var\(--paper-transition-half-gap\)\)/s);
  assert.match(css,/\.profile-page \.munge-control\s*\{[^}]*width:\s*var\(--munge-control-width\)/s);
  assert.match(css,/\.profile-page \.munge-control\s*\{[^}]*pointer-events:\s*none/s);
  assert.match(css,/\.profile-page \.munge-body-button\s*\{[^}]*pointer-events:\s*auto/s);
  assert.match(css,/@media \(max-width: 620px\)[\s\S]*?--munge-control-width:\s*min\(88vw, 330px\)/);
});
