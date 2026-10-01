/* Physical source picker: pointer motion only deforms; native button click activates. */
(function(root) {
    class SourceUdder {
        constructor({udder, buttons, layer, reduced=()=>false, raf=fn=>requestAnimationFrame(fn),
                     now=()=>performance.now(), schedule=(fn, ms)=>setTimeout(fn, ms)}) {
            Object.assign(this, {udder, buttons:[...buttons], layer, reduced, raf, now, schedule});
            this.states = this.buttons.map(() => ({position:0, velocity:0, target:0, lastX:null, lastTime:null, frame:false}));
            this.buttons.forEach((button, index) => this.bind(button, index));
        }
        bind(button, index) {
            button.addEventListener('pointerenter', event => this.track(index, event));
            button.addEventListener('pointermove', event => this.flick(index, event));
            button.addEventListener('pointerleave', () => this.release(index));
            button.addEventListener('pointercancel', () => this.release(index));
            button.addEventListener('click', () => this.activate(index));
        }
        track(index, event) {
            if (event.pointerType === 'touch' || this.reduced()) return;
            const state=this.states[index]; state.lastX=event.clientX; state.lastTime=this.now();
        }
        flick(index, event) {
            if (event.pointerType === 'touch' || this.reduced()) return;
            const state=this.states[index], time=this.now();
            if (state.lastX === null) return this.track(index, event);
            const elapsed=Math.max(8, time-state.lastTime), dx=event.clientX-state.lastX;
            const speed=Math.min(2.2, Math.abs(dx)/elapsed);
            const direction=Math.sign(dx) || 1;
            state.target=direction*Math.min(24, 4+speed*10);
            state.velocity+=direction*speed*2.4;
            state.lastX=event.clientX; state.lastTime=time;
            if (speed>1) this.neighbourImpulse(index, direction*speed);
            this.animate(index);
        }
        neighbourImpulse(index, impulse) {
            for (const neighbour of [index-1,index+1]) {
                if (!this.states[neighbour]) continue;
                this.states[neighbour].velocity+=impulse*.28;
                this.animate(neighbour);
            }
        }
        release(index) {
            const state=this.states[index]; state.target=0; state.lastX=null; state.lastTime=null;
            this.animate(index);
        }
        animate(index) {
            const state=this.states[index];
            if (state.frame || this.reduced()) return;
            state.frame=true;
            const step=()=>{
                state.target*=.72;
                state.velocity+=(state.target-state.position)*.18;
                state.velocity*=.78;
                state.position+=state.velocity;
                this.render(index);
                if (Math.abs(state.position)>.08 || Math.abs(state.velocity)>.08 || Math.abs(state.target)>.08) {
                    this.raf(step);
                } else {
                    state.position=state.velocity=state.target=0; state.frame=false; this.render(index);
                }
            };
            this.raf(step);
        }
        render(index) {
            const shape=this.buttons[index].querySelector('.teat-shape'), bend=this.states[index].position;
            shape.style.setProperty('--bend', `${bend.toFixed(2)}deg`);
            shape.style.setProperty('--rotate', `${(bend*.32).toFixed(2)}deg`);
            shape.style.setProperty('--shift', `${(bend*.42).toFixed(2)}px`);
            shape.style.setProperty('--stretch', String(1+Math.min(.12,Math.abs(bend)/190)));
            shape.style.setProperty('--squash', String(1-Math.min(.06,Math.abs(bend)/380)));
        }
        activate(index) {
            const button=this.buttons[index], shape=button.querySelector('.teat-shape');
            shape.classList.remove('squeezed'); void shape.offsetWidth; shape.classList.add('squeezed');
            this.schedule(()=>shape.classList.remove('squeezed'), 260);
            if (!this.reduced()) this.splash(button, button.dataset.liquid);
        }
        splash(button, colour) {
            const tip=button.getBoundingClientRect(), parchment=document.querySelector('.profile-container').getBoundingClientRect();
            const startX=tip.left+tip.width/2, startY=tip.bottom-5;
            const impactX=Math.max(parchment.left+55,Math.min(parchment.right-55,startX+(Math.random()-.5)*90));
            const impactY=Math.max(startY+85,Math.min(parchment.bottom-70,parchment.top+parchment.height*.48));
            const spurt=document.createElement('span'); spurt.className='udder-spurt';
            spurt.style.setProperty('--liquid',colour);spurt.style.setProperty('--start-x',`${startX}px`);spurt.style.setProperty('--start-y',`${startY}px`);
            spurt.style.setProperty('--travel-x',`${impactX-startX}px`);spurt.style.setProperty('--travel-y',`${impactY-startY}px`);
            spurt.style.setProperty('--travel-angle',`${(impactX-startX)*.08}deg`);this.layer.appendChild(spurt);
            this.schedule(()=>{spurt.remove();this.impact(impactX,impactY,colour,parchment);},410);
        }
        impact(x,y,colour,parchment) {
            const splash=document.createElement('span');splash.className='udder-splash';
            const width=parchment.width*(.68+Math.random()*.14), height=parchment.height*(.58+Math.random()*.15);
            x=Math.max(parchment.left+width*.42,Math.min(parchment.right-width*.42,x));
            y=Math.max(parchment.top+height*.42,Math.min(parchment.bottom-height*.42,y));
            splash.style.setProperty('--impact-x',`${x}px`);splash.style.setProperty('--impact-y',`${y}px`);splash.style.setProperty('--liquid',colour);
            splash.style.setProperty('--spill-width',`${width}px`);splash.style.setProperty('--spill-height',`${height}px`);
            splash.style.setProperty('--spill-radius',`${35+Math.random()*20}% ${45+Math.random()*20}% ${32+Math.random()*22}% ${42+Math.random()*20}% / ${42+Math.random()*18}% ${34+Math.random()*20}% ${48+Math.random()*18}% ${36+Math.random()*22}%`);
            const edge=[[2,41],[9,25],[21,20],[27,5],[38,16],[50,1],[59,15],[75,8],[79,24],[96,29],[88,46],[100,59],[83,68],[87,89],[69,83],[58,99],[47,84],[30,96],[25,78],[7,76],[14,59]];
            splash.style.setProperty('--spill-shape',`polygon(${edge.map(([a,b])=>`${Math.max(0,Math.min(100,a+(Math.random()-.5)*7))}% ${Math.max(0,Math.min(100,b+(Math.random()-.5)*7))}%`).join(',')})`);
            splash.style.setProperty('--run-x',`${25+Math.random()*50}%`);
            const blot=document.createElement('span');blot.className='udder-blot';splash.appendChild(blot);
            for(let i=0;i<14;i++){
                const drop=document.createElement('i');drop.className='udder-drop';
                drop.style.setProperty('--size',`${8+(i%4)*6}px`);
                drop.style.setProperty('--drop-x',`${Math.round((Math.random()-.5)*width*1.16+width/2)}px`);
                drop.style.setProperty('--drop-y',`${Math.round((Math.random()-.5)*height*1.12+height/2)}px`);splash.appendChild(drop);
            }
            this.layer.appendChild(splash);this.schedule(()=>splash.remove(),4100);
        }
    }
    if(typeof module!=='undefined')module.exports={SourceUdder};
    if(typeof document==='undefined')return;
    const udder=document.getElementById('sourceUdder');
    if(!udder)return;
    const layer=document.createElement('div');layer.className='udder-liquid-layer';layer.setAttribute('aria-hidden','true');document.body.appendChild(layer);
    root.sourceUdder=new SourceUdder({udder,buttons:udder.querySelectorAll('.udder-teat'),layer,
        reduced:()=>!!root.matchMedia?.('(prefers-reduced-motion: reduce)').matches});
})(typeof globalThis!=='undefined'?globalThis:this);
