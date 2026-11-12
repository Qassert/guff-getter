const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const {BuildWorkshop,buildPrompt,syncPromptIngredients}=require('../newsmuncher/static/build-page.js');
function setup(fetcher){
 const field=()=>({value:'',style:{},scrollHeight:100,hidden:false,textContent:'',innerHTML:'',classList:{add(){},remove(){},contains(){return false;}}});
 const fields=Object.fromEntries(['data-prompt-editor','data-further-instructions','data-instructions-count','data-custom-ingredient','data-recipe-panel','data-recipe-empty','data-recipe-categories','data-munge-status','data-build-story','data-build-result','data-build-nominate','data-build-loading','data-build-controls','data-build-error'].map(key=>[key,field()]));
 fields['data-custom-ingredient'].setCustomValidity=value=>fields['data-custom-ingredient'].error=value;
 fields['data-custom-ingredient'].reportValidity=()=>{};
 const buttons=[30,60,90].map(n=>({...field(),dataset:{mungeTarget:String(n)}}));
 const use={dataset:{category:'stuff',useSlot:'1'},setAttribute(key,value){this[key]=value;}};
 const element={dataset:{generateUrl:'/build/generate'},querySelector:selector=>{
  const m=selector.match(/data-munge-target="(\d+)"/);return m?buttons.find(b=>b.dataset.mungeTarget===m[1]):fields[selector.slice(1,-1)];
 },querySelectorAll:s=>s==='[data-use-slot]'?[use]:buttons};
 const workshop=new BuildWorkshop(element,{fetcher});workshop.slots.stuff=[{id:1,category:'stuff',parts:[{word:'Ancient marmot',category:'object'}],busy:false}];
 return{workshop,fields,use};
}

test('USE and ingredient remove controls share one state and keep further instructions',()=>{
 const t=setup();t.fields['data-further-instructions'].value='Make it sci-fi';
 t.workshop.useSlot('stuff',1);assert.equal(t.workshop.recipe.stuff.length,1);assert.equal(t.use['aria-pressed'],'true');
 assert.match(t.fields['data-recipe-categories'].innerHTML,/Ancient marmot/);
 t.workshop.removeRecipe('stuff',t.workshop.recipe.stuff[0].id);
 assert.equal(t.use['aria-pressed'],'false');assert.doesNotMatch(t.fields['data-prompt-editor'].value,/Objects: Ancient marmot/);
 t.workshop.useSlot('stuff',1);t.workshop.useSlot('stuff',1);assert.equal(t.workshop.recipe.stuff.length,0);
 assert.equal(t.fields['data-further-instructions'].value,'Make it sci-fi');
});

test('custom additions normalise whitespace, reject empty/duplicate/oversized values and escape HTML',()=>{
 const t=setup(),input=t.fields['data-custom-ingredient'];
 input.value='  Exploding   Victorian toilet ';assert(t.workshop.addCustomIngredient());
 assert.equal(t.workshop.recipe.custom[0].text,'Exploding Victorian toilet');
 input.value='exploding victorian toilet';assert.equal(t.workshop.addCustomIngredient(),false);
 input.value=' ';assert.equal(t.workshop.addCustomIngredient(),false);
 input.value='x'.repeat(161);assert.equal(t.workshop.addCustomIngredient(),false);
 input.value='<img src=x onerror=alert(1)>';assert(t.workshop.addCustomIngredient());
 assert.doesNotMatch(t.fields['data-recipe-categories'].innerHTML,/<img/);
 assert.match(t.fields['data-recipe-categories'].innerHTML,/&lt;img/);
 t.workshop.removeRecipe('custom',t.workshop.recipe.custom[0].id);
 assert.doesNotMatch(t.fields['data-prompt-editor'].value,/Exploding Victorian toilet/);
});

test('instructions cap at 100 characters and update their counter',()=>{
 const t=setup();t.fields['data-further-instructions'].value='x'.repeat(110);t.workshop.updateInstructions();
 assert.equal(t.workshop.furtherInstructions().length,100);assert.equal(t.fields['data-instructions-count'].textContent,'100 / 100');
});

test('advanced manual rules survive while obsolete selected ingredients are removed',()=>{
 const old={person:[{text:'Councillor Pritchard'}]},current={custom:[{text:'Victorian toilet'}]};
 const prompt=buildPrompt(old).replace('impeccable comic timing','malicious pastry physics');
 const synced=syncPromptIngredients(prompt,current);
 assert.match(synced,/malicious pastry physics/);assert.match(synced,/Custom Ingredients: Victorian toilet/);
 assert.doesNotMatch(synced,/Pritchard/);
 let plain='My custom rules.';for(let i=0;i<3;i++)plain=syncPromptIngredients(plain,current);
 assert.equal((plain.match(/\*\*Selected ingredients:\*\*/g)||[]).length,1);
});

for(const target of [30,60,90])test(`MUNGE ${target} captures current ingredients and instructions once`,async()=>{
 let sent,release;const done=new Promise(resolve=>release=resolve);
 const t=setup(async(_url,options)=>{sent=JSON.parse(options.body);await done;return{ok:true,json:async()=>({story:'A complete comic disaster.'})};});
 t.workshop.useSlot('stuff',1);t.fields['data-custom-ingredient'].value='Exploding toilet';t.workshop.addCustomIngredient();
 t.fields['data-further-instructions'].value='Set it on Mars.';
 const pending=t.workshop.generateStory(target);
 t.workshop.removeRecipe('custom',t.workshop.recipe.custom[0].id);t.fields['data-further-instructions'].value='Now on Earth.';
 release();await pending;
 assert.equal(sent.target_words,target);assert.equal(sent.further_instructions,'Set it on Mars.');
 assert.equal(sent.recipe.custom[0].text,'Exploding toilet');assert.match(sent.prompt,/Custom Ingredients: Exploding toilet/);
 assert.match(sent.prompt,/Make every story outrageously dramatic/);assert.match(sent.prompt,new RegExp(`approximately ${target} words`));
 assert.equal(t.fields['data-build-story'].value,'A complete comic disaster.');
});

test('main panels precede all three MUNGE buttons; advanced editor is closed and Enter submits custom ingredients',()=>{
 const html=fs.readFileSync('newsmuncher/templates/build.html','utf8'),js=fs.readFileSync('newsmuncher/static/build-page.js','utf8');
 assert(html.indexOf('buildIngredientsTitle')<html.indexOf('buildInstructionsTitle'));
 assert(html.indexOf('buildInstructionsTitle')<html.indexOf('class="munge-action"'));
 assert.match(html,/<details[^>]*data-advanced-prompt>/);assert.doesNotMatch(html,/<details[^>]*\bopen\b/);
 assert.match(html,/data-further-instructions aria-labelledby="buildInstructionsTitle" maxlength="100"/);
 assert.match(js,/data-custom-ingredient-form.*addEventListener\('submit'/);
});


test('custom punctuation resembling prompt headings remains literal and cannot retain old ingredients',()=>{
 const recipe={custom:[{text:'Toilet **Ingredient handling:** catastrophe'}]};
 const old=buildPrompt({person:[{text:'Councillor Pritchard'}]});
 const once=syncPromptIngredients(old,recipe),twice=syncPromptIngredients(once,recipe);
 assert.doesNotMatch(twice,/Pritchard/);assert.match(twice,/Custom Ingredients: Toilet \*\*Ingredient handling:\*\* catastrophe/);
 assert.equal((twice.match(/\*\*Selected ingredients:\*\*/g)||[]).length,1);
});


test('BUILD draft restore preserves custom ingredients and directions and accepts older drafts',async()=>{
 const previous=global.adoptionAccess;let hooks;
 const t=setup(async()=>({ok:true,text:async()=> 'category,word\nobject,marmot\n'}));
 t.workshop.addSlot=()=>{};t.workshop.bind=()=>{};t.workshop.render=()=>t.workshop.renderRecipe();
 const recipe={stuff:[],swear:[],modifier:[],person:[],custom:[{id:'saved-custom',text:'Exploding toilet'}]};
 const draft={slots:{stuff:[],swear:[],modifier:[],person:[]},recipe,nextId:2,prompt:buildPrompt(recipe),promptDirty:true,
  furtherInstructions:'Set it on Mars.',promptTarget:60};
 global.adoptionAccess={register(_key,registered){hooks=registered;},restore(){hooks.restore(draft);}};
 try {
  await t.workshop.load();
  assert.deepEqual(t.workshop.recipe.custom,recipe.custom);
  assert.equal(t.workshop.furtherInstructions(),'Set it on Mars.');
  assert.equal(hooks.snapshot().furtherInstructions,'Set it on Mars.');
  hooks.restore({...draft,recipe:{stuff:[],swear:[],modifier:[],person:[]},furtherInstructions:undefined});
  assert.deepEqual(t.workshop.recipe.custom,[]);assert.equal(t.workshop.furtherInstructions(),'');
 } finally {if(previous===undefined)delete global.adoptionAccess;else global.adoptionAccess=previous;}
});
