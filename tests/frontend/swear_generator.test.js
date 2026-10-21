const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {CATEGORIES, STRUCTURES, parseCSV, copyPlainText, SwearGenerator} = require(
    '../../newsmuncher/static/js/creation/swear-generator.js');

const originalCSV = fs.readFileSync(
    'newsmuncher/static/data/swear-generator-vocabulary.csv', 'utf8');

test('CSV preserves all four authoritative collections and supports safe extensions', () => {
    const vocabulary = parseCSV(originalCSV + '\nzelfs_nw,"new, multi-word thing"\n' +
        'zelfs_nw,"new, multi-word thing"\nunknown,nope\nbroken,row,extra\n,\n');
    assert.deepEqual(CATEGORIES, ['bijv_nw', 'gilles', 'zelfs_nw', 'handelend']);
    assert.deepEqual(CATEGORIES.map(category => vocabulary[category].length), [440, 141, 71, 105]);
    assert(vocabulary.zelfs_nw.includes('new, multi-word thing'));
    assert(vocabulary.bijv_nw.includes('risqué'));
    assert(vocabulary.gilles.includes('ball sack'));
});

test('all six original phrase structures retain their category order', () => {
    assert.deepEqual(STRUCTURES, [
        ['bijv_nw', 'gilles', 'zelfs_nw'],
        ['bijv_nw', 'gilles', 'handelend'],
        ['bijv_nw', 'zelfs_nw', 'handelend'],
        ['gilles', 'zelfs_nw'],
        ['gilles', 'handelend'],
        ['zelfs_nw', 'handelend']
    ]);
    const vocabulary = Object.fromEntries(CATEGORIES.map(category => [category, [category + ' word']]));
    const generator = new SwearGenerator(vocabulary, {random: () => 0});
    for (const structure of STRUCTURES)
        assert.deepEqual(generator.candidate(structure).map(slot => slot.category), structure);
});

test('five 100ms flicks overlap the next word after the third flick', async () => {
    const vocabulary = Object.fromEntries(CATEGORIES.map(category => [category,
        [0,1,2,3,4,5].map(value => category + value)]));
    const queue = [], events = [];
    const generator = new SwearGenerator(vocabulary, {
        random: () => 0,
        schedule(fn, delay) { queue.push({fn, delay}); return fn; },
        cancel() {},
        reducedMotion: () => false,
        display(event) { events.push({index:event.index, final:event.final}); }
    });
    const pending = generator.generate();
    while (queue.length) {
        const task = queue.shift();
        assert.equal(task.delay, 100);
        task.fn();
    }
    await pending;
    assert.equal(events.filter(event => event.index === 0).length, 5);
    const firstSecond = events.findIndex(event => event.index === 1);
    const firstFinal = events.findIndex(event => event.index === 0 && event.final);
    assert(firstSecond > -1 && firstSecond < firstFinal);
});

test('slot regeneration keeps other words and prefers a different category value', async () => {
    const vocabulary = {
        bijv_nw:['red','blue'], gilles:['thing','widget'],
        zelfs_nw:['bucket','barrel'], handelend:['licker','polisher']
    };
    const events=[];
    const generator = new SwearGenerator(vocabulary, {
        random: () => .99, reducedMotion: () => true,
        display:event => events.push(event)
    });
    generator.slots = [
        {category:'bijv_nw',word:'red'}, {category:'gilles',word:'thing'},
        {category:'zelfs_nw',word:'bucket'}
    ];
    const before = generator.slots.map(slot => slot.word);
    await generator.replacement(1);
    assert.deepEqual(generator.slots.map(slot => slot.word), ['red','widget','bucket']);
    assert.deepEqual(generator.slots.filter((_, index) => index !== 1).map(slot => slot.word),
        [before[0], before[2]]);
    assert.equal(events.length, 1);
});

test('finite spaces exhaust exactly, reset, and never loop indefinitely', async () => {
    const vocabulary = {bijv_nw:['a'],gilles:['b'],zelfs_nw:['c'],handelend:['d']};
    const generator = new SwearGenerator(vocabulary, {random: () => 0, reducedMotion: () => true});
    const phrases=[];
    for (let index=0; index<6; index++) phrases.push(await generator.generate());
    assert.equal(new Set(phrases).size, 6);
    const repeated = await generator.generate();
    assert(phrases.includes(repeated));
    assert.equal(generator.used.size, 1);
});

test('completed combinations seed and update bounded browser-session history', async () => {
    const updates=[];
    const vocabulary = {bijv_nw:['a','e'],gilles:['b'],zelfs_nw:['c'],handelend:['d']};
    const generator = new SwearGenerator(vocabulary, {
        random:()=>0, reducedMotion:()=>true, initialUsed:['a\u001fb\u001fc'],
        usedLimit:2, onUsed:values=>updates.push(values)
    });
    const phrase=await generator.generate();
    assert.notEqual(phrase,'A b c');
    assert.equal(updates.length,1);
    assert(updates[0].length<=2);
});

test('a one-word slot remains stable and reduced motion performs no scheduling', async () => {
    let scheduled=0;
    const vocabulary = {bijv_nw:['only'],gilles:['one'],zelfs_nw:['choice'],handelend:['here']};
    const generator = new SwearGenerator(vocabulary, {
        reducedMotion: () => true, schedule() { scheduled++; }
    });
    generator.slots=[{category:'gilles',word:'one'}];
    assert.equal(await generator.replacement(0), 'One');
    assert.equal(scheduled,0);
});

test('a new generation cancels timers and settles the superseded operation', async () => {
    const vocabulary = Object.fromEntries(CATEGORIES.map(category => [category,['a','b']]));
    const queue=[];
    const generator = new SwearGenerator(vocabulary, {
        random:()=>0, reducedMotion:()=>false,
        schedule(fn){queue.push(fn); return fn;}, cancel(timer){
            const index=queue.indexOf(timer); if(index>=0) queue.splice(index,1);
        }
    });
    const first=generator.generate();
    const rejected=assert.rejects(first,error=>error.name==='AbortError');
    const second=generator.generate();
    while(queue.length) queue.shift()();
    await Promise.all([rejected,second]);
    assert.equal(generator.busy,false);
});

test('Create mounts the standalone component without analytics or MUNGE coupling', () => {
    const template=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8');
    const script=fs.readFileSync('newsmuncher/static/js/creation/swear-generator.js','utf8');
    assert.match(template,/data-swear-generator/);
    assert.match(template,/data\/swear-generator-vocabulary\.csv/);
    assert.match(template,/js\/creation\/swear-generator\.js/);
    assert.match(template,/data-swear-generate>SWEAR<\/button>/);
    assert.match(template,/data-swear-copy disabled>COPY<\/button>/);
    assert.doesNotMatch(template,/SWEAR-WORD GENERATOR|Recent creations|data-swear-history/);
    assert.doesNotMatch(script,/Click any word to replace it|data-swear-history|recordHistory/);
    assert.doesNotMatch(script,/StatCounter|statcounter|fetch\([^)]*https?:|MUNGE|nominate|promotion-gallery/i);
});

test('generator is between the response editor and image without changing either element',()=>{
    const template=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8');
    const editor=template.indexOf('id="responseEditor"');
    const generator=template.indexOf('data-swear-generator');
    const image=template.indexOf('id="imagePanel"');
    assert(editor>-1 && generator>editor && image>generator);
});

test('COPY writes the complete plain phrase and safely falls back',async()=>{
    const writes=[];
    assert.equal(await copyPlainText('Hard-rubbing pile licker',{
        clipboard:{writeText:async text=>writes.push(text)}, document:null
    }),true);
    assert.deepEqual(writes,['Hard-rubbing pile licker']);

    let selected=false,removed=false,appended=false;
    const field={style:{},select(){selected=true;},remove(){removed=true;}};
    const document={body:{appendChild(node){appended=node===field;}},
        createElement:()=>field,execCommand:command=>command==='copy'};
    assert.equal(await copyPlainText('Fallback phrase',{
        clipboard:{writeText:async()=>{throw new Error('denied');}},document
    }),true);
    assert.equal(field.value,'Fallback phrase');
    assert(field.readOnly && selected && removed && appended);
    assert.equal(await copyPlainText('',{clipboard:null,document}),false);
    assert.equal(await copyPlainText('No access',{clipboard:null,document:null}),false);
});

test('COPY remains disabled until completion and during generation or slot replacement',()=>{
    const template=fs.readFileSync('newsmuncher/templates/pet_profile.html','utf8');
    const script=fs.readFileSync('newsmuncher/static/js/creation/swear-generator.js','utf8');
    assert.match(template,/data-swear-copy disabled/);
    assert.match(script,/generate\.disabled = true; copy\.disabled = true/);
    assert.match(script,/generator\.generate\(\); status\.textContent = ''; copy\.disabled = false/);
    assert.match(script,/button\.disabled = true; status\.textContent = 'Replacing word…'/);
    assert.match(script,/generator\.replacement\(index\)[\s\S]*copy\.disabled = false/);
    assert.match(script,/copy\.textContent = 'COPIED'/);
});

test('minimal styling is one transparent horizontal row with plain clickable words',()=>{
    const css=fs.readFileSync('newsmuncher/static/css/creation/swear-generator.css','utf8');
    const panel=css.split('.profile-page .swear-generator {',2)[1].split('}',1)[0];
    const output=css.split('.profile-page .swear-generator-output {',2)[1].split('}',1)[0];
    const slot=css.split('.profile-page .swear-word-slot {',2)[1].split('}',1)[0];
    assert.match(panel,/display:flex/); assert.match(panel,/align-items:center/);
    assert.doesNotMatch(panel,/background|box-shadow|border:/);
    assert.match(output,/flex-wrap:wrap/); assert.match(output,/justify-content:flex-start/);
    assert.match(slot,/border:0/); assert.doesNotMatch(slot,/dotted|text-decoration/);
});
