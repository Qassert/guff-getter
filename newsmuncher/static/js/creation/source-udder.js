/* Physical source picker: pointer motion only deforms; native button click activates. */
(function(root) {
    // Deliberately centralized for the next visual-tuning pass.
    const TEAT_ORIGIN_OFFSETS=Object.freeze([
        {x:-45,y:-12}, {x:-30,y:0}, {x:0,y:0}, {x:30,y:-20}, {x:40,y:-20}
    ]);
    const EFFECT_SCALE=2;

    class UdderEffectsCanvas {
        constructor({reduced=()=>false}={}) {
            this.reduced=reduced;this.effects=[];this.active=new Set();this.frame=0;
            this.canvas=document.createElement('canvas');
            this.canvas.className='udder-cream-canvas';this.canvas.setAttribute('aria-hidden','true');
            (document.querySelector('.profile-container')||document.body).appendChild(this.canvas);
            this.context=this.canvas.getContext('2d');
            this.resize=()=>this.size();root.addEventListener('resize',this.resize,{passive:true});this.size();
        }
        size() {
            const ratio=Math.min(2,root.devicePixelRatio||1),width=root.innerWidth,height=root.innerHeight;
            if(this.canvas.width===Math.round(width*ratio)&&this.canvas.height===Math.round(height*ratio))return;
            this.canvas.width=Math.round(width*ratio);this.canvas.height=Math.round(height*ratio);
            this.canvas.style.width=`${width}px`;this.canvas.style.height=`${height}px`;
            this.context.setTransform(ratio,0,0,ratio,0,0);
        }
        isActive(index) { return this.active.has(index); }
        reserve(index) { this.active.add(index); }
        start(index,teat) {
            if(this.reduced()) { setTimeout(()=>this.active.delete(index),240);return; }
            const tip=teat.getBoundingClientRect(),paper=document.querySelector('.profile-container').getBoundingClientRect();
            const adjustment=TEAT_ORIGIN_OFFSETS[index]||{x:0,y:0};
            const start={x:tip.left+tip.width/2+adjustment.x,y:tip.bottom-7+adjustment.y};
            const impact={
                x:Math.max(paper.left+70,Math.min(paper.right-70,start.x+(Math.random()-.5)*40)),
                y:Math.min(paper.bottom-75,Math.max(start.y+105,paper.top+paper.height*.34))
            };
            const now=performance.now(),random=()=>Math.random();
            const kinds=['cream','foam','cream','pressure','foam'],durations=[5200,5700,5200,3800,5700];
            if(index===3)impact.x=Math.max(paper.left+95,Math.min(paper.right-95,paper.left+paper.width*.28));
            const effect={index,kind:kinds[index],duration:durations[index],start,impact,born:now,scrollX:root.scrollX,scrollY:root.scrollY,
                phase:random()*Math.PI*2,
                edge:Array.from({length:18},(_,i)=>.78+random()*.38+(i%3===0?random()*.16:0)),
                drops:Array.from({length:5},(_,i)=>({birth:360+i*155+random()*110,dx:(random()-.5)*55,
                    drift:(random()-.5)*18,size:3+random()*5})),
                bubbles:Array.from({length:38},(_,i)=>({birth:100+i*38+random()*160,size:4+random()*13,
                    lane:(random()-.5)*42,drift:(random()-.5)*32,life:900+random()*900})),
                creatures:Array.from({length:6},(_,i)=>({birth:i*155+random()*90,size:11+random()*7,
                    vx:(random()-.5)*48,colour:`hsl(${18+random()*42} 72% ${60+random()*10}%)`,look:random()>.78}))};
            this.effects.push(effect);
            if(!this.frame)this.frame=requestAnimationFrame(time=>this.draw(time));
        }
        offset(effect) { return {x:effect.scrollX-root.scrollX,y:effect.scrollY-root.scrollY}; }
        stream(effect,age,offset) {
            const ctx=this.context,start={x:effect.start.x+offset.x,y:effect.start.y+offset.y};
            const end={x:effect.impact.x+offset.x,y:effect.impact.y+offset.y};
            const fall=Math.min(1,age/720),tail=Math.max(0,Math.min(1,(age-1120)/260));
            if(age>1380)return;
            const headY=start.y+(end.y-start.y)*(1-Math.pow(1-fall,2));
            const headX=start.x+(end.x-start.x)*fall;
            const points=[];
            for(let i=0;i<=16;i++) {
                const t=tail+(1-tail)*i/16,y=start.y+(headY-start.y)*t;
                const wobble=Math.sin(t*10+effect.phase+age*.009)*(2.2+5*t)+Math.sin(t*23+effect.phase)*1.8;
                const x=start.x+(headX-start.x)*t+wobble;
                const neck=.82+.2*Math.sin(t*17+effect.phase)+.12*Math.sin(t*31-age*.006);
                points.push({x,y,r:(6.5+4.5*t)*Math.max(.58,neck)});
            }
            ctx.save();ctx.shadowColor='rgba(68,43,20,.32)';ctx.shadowBlur=5;ctx.shadowOffsetY=3;
            this.ribbon(points,'#f5e7c3');ctx.restore();
            ctx.save();ctx.globalAlpha=.62;this.ribbon(points.map(point=>({...point,x:point.x-1.8,r:Math.max(1,point.r*.22)})),'#fffdf0');ctx.restore();
            const bulge=points[points.length-1];
            ctx.beginPath();ctx.fillStyle='#f5e7c3';ctx.ellipse(bulge.x,bulge.y,bulge.r*1.12,bulge.r*1.42,0,0,Math.PI*2);ctx.fill();
        }
        ribbon(points,colour) {
            const ctx=this.context;ctx.beginPath();
            points.forEach((point,index)=>index?ctx.lineTo(point.x-point.r,point.y):ctx.moveTo(point.x-point.r,point.y));
            for(let i=points.length-1;i>=0;i--)ctx.lineTo(points[i].x+points[i].r,points[i].y);
            ctx.closePath();ctx.fillStyle=colour;ctx.fill();
            points.forEach(point=>{ctx.beginPath();ctx.arc(point.x,point.y,point.r,0,Math.PI*2);ctx.fill();});
        }
        puddle(effect,age,offset) {
            if(age<610)return;
            const ctx=this.context,p=Math.min(1,(age-610)/700),fade=age<4300?1:Math.max(0,1-(age-4300)/850);
            const x=effect.impact.x+offset.x,y=effect.impact.y+offset.y;
            ctx.save();ctx.globalAlpha=fade;ctx.shadowColor='rgba(64,38,14,.36)';ctx.shadowBlur=7;ctx.shadowOffsetY=4;
            const gradient=ctx.createRadialGradient(x-18*p,y-7*p,3,x,y,78*p);
            gradient.addColorStop(0,'#fffbea');gradient.addColorStop(.48,'#f6e8c5');gradient.addColorStop(1,'#ddc99d');
            ctx.beginPath();
            effect.edge.forEach((edge,index)=>{
                const angle=index/effect.edge.length*Math.PI*2,rx=76*p*edge,ry=30*p*(.86+edge*.16);
                const px=x+Math.cos(angle)*rx,py=y+Math.sin(angle)*ry;
                index?ctx.lineTo(px,py):ctx.moveTo(px,py);
            });
            ctx.closePath();ctx.fillStyle=gradient;ctx.fill();ctx.restore();
            ctx.save();ctx.globalAlpha=fade*.55;ctx.fillStyle='#fffdf1';ctx.beginPath();ctx.ellipse(x-15*p,y-7*p,30*p,5*p,-.08,0,Math.PI*2);ctx.fill();ctx.restore();
            for(let i=0;i<7;i++) {
                const angle=effect.phase+i*2.17,distance=(54+(i%3)*17)*p,size=(3+(i%4)*1.7)*Math.min(1,p*2);
                ctx.save();ctx.globalAlpha=fade*.9;ctx.fillStyle='#f3e3bc';ctx.beginPath();
                ctx.ellipse(x+Math.cos(angle)*distance,y+Math.sin(angle)*distance*.42,size,size*.72,angle,0,Math.PI*2);ctx.fill();ctx.restore();
            }
        }
        droplets(effect,age,offset) {
            const ctx=this.context,startX=effect.start.x+offset.x,startY=effect.start.y+offset.y;
            effect.drops.forEach(drop=>{
                const elapsed=age-drop.birth;if(elapsed<0||elapsed>900)return;
                const t=elapsed/1000,x=startX+drop.dx+drop.drift*t,y=startY+24+75*t+260*t*t;
                ctx.save();ctx.globalAlpha=Math.min(1,(900-elapsed)/180);ctx.fillStyle='#f5e7c3';ctx.shadowColor='#4a2d1838';ctx.shadowBlur=3;
                ctx.beginPath();ctx.ellipse(x,y,drop.size,drop.size*(1.15+Math.min(.8,t)),0,0,Math.PI*2);ctx.fill();ctx.restore();
            });
        }
        bubble(x,y,r,alpha=1) {
            const ctx=this.context;
            ctx.save();ctx.globalAlpha=alpha;ctx.fillStyle='rgba(247,250,229,.58)';ctx.strokeStyle='rgba(191,208,183,.78)';
            ctx.lineWidth=Math.max(1,r*.11);ctx.shadowColor='rgba(50,66,45,.22)';ctx.shadowBlur=3;
            ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();ctx.stroke();
            ctx.fillStyle='rgba(255,255,255,.82)';ctx.beginPath();ctx.ellipse(x-r*.3,y-r*.34,r*.24,r*.13,-.55,0,Math.PI*2);ctx.fill();ctx.restore();
        }
        runFoamEffect(effect,age,offset) {
            const sx=effect.start.x+offset.x,sy=effect.start.y+offset.y,ix=effect.impact.x+offset.x,iy=effect.impact.y+offset.y;
            const fade=age<4600?1:Math.max(0,1-(age-4600)/1050);
            effect.bubbles.forEach((bubble,index)=>{
                const elapsed=age-bubble.birth;if(elapsed<0||elapsed>bubble.life)return;
                const t=elapsed/bubble.life,fall=Math.min(1,elapsed/760),x=sx+bubble.lane*(.2+fall)+bubble.drift*t;
                const y=sy+(iy-sy)*(1-Math.pow(1-fall,2));
                const pop=t>.82?(1-t)/.18:1,size=bubble.size*(.55+Math.min(1,t*4)*.55);
                this.bubble(x,y,size,fade*Math.max(0,pop));
            });
            if(age>650) {
                const build=Math.min(1,(age-650)/950),ctx=this.context;
                for(let i=0;i<25;i++) {
                    const row=Math.floor(i/8),column=i%8,spread=(column-3.5)*16+(row%2)*7;
                    const r=(7+(i*7%11))*build,wobble=Math.sin(age*.002+i)*1.6;
                    this.bubble(ix+spread+wobble,iy-row*13-Math.abs(spread)*.035,r,fade);
                }
                ctx.save();ctx.globalAlpha=fade*.3;ctx.fillStyle='#f8f8df';ctx.beginPath();ctx.ellipse(ix,iy+8,78*build,19*build,0,0,Math.PI*2);ctx.fill();ctx.restore();
            }
        }
        runSlimeEffect(effect,age,offset) {
            const ctx=this.context,s={x:effect.start.x+offset.x,y:effect.start.y+offset.y},end={x:effect.impact.x+offset.x,y:effect.impact.y+offset.y};
            const fall=Math.min(1,age/1500),fade=age<5000?1:Math.max(0,1-(age-5000)/950);
            if(age<2800) {
                const headY=s.y+(end.y-s.y)*(fall*fall),headX=s.x+(end.x-s.x)*fall,tail=Math.max(0,(age-2050)/760),points=[];
                for(let i=0;i<=18;i++) {
                    const t=tail+(1-tail)*i/18;
                    points.push({x:s.x+(headX-s.x)*t+Math.sin(t*15+effect.phase)*3.2,
                        y:s.y+(headY-s.y)*t,r:(7+8*t)*(.62+.32*Math.sin(t*20+1.5))});
                }
                ctx.save();ctx.globalAlpha=fade;ctx.shadowColor='#173b16aa';ctx.shadowBlur=6;this.ribbon(points,'#397c2d');ctx.restore();
                ctx.save();ctx.globalAlpha=.7*fade;this.ribbon(points.map(p=>({...p,x:p.x-2,r:Math.max(1,p.r*.2)})),'#9ed66b');ctx.restore();
                const glob=points[points.length-1];ctx.save();ctx.globalAlpha=fade;ctx.fillStyle='#397c2d';ctx.beginPath();ctx.ellipse(glob.x,glob.y,19,24,0,0,Math.PI*2);ctx.fill();ctx.restore();
            }
            if(age>1250) {
                const p=Math.min(1,(age-1250)/1100),x=end.x,y=end.y;
                ctx.save();ctx.globalAlpha=fade;ctx.shadowColor='#18391399';ctx.shadowBlur=7;ctx.fillStyle='#326f2b';ctx.beginPath();
                effect.edge.forEach((edge,i)=>{const a=i/effect.edge.length*Math.PI*2,px=x+Math.cos(a)*70*p*edge,py=y+Math.sin(a)*27*p*edge;i?ctx.lineTo(px,py):ctx.moveTo(px,py);});
                ctx.closePath();ctx.fill();ctx.fillStyle='#90cc61';ctx.globalAlpha=fade*.58;ctx.beginPath();ctx.ellipse(x-13,y-7,28*p,5*p,-.1,0,Math.PI*2);ctx.fill();ctx.restore();
                if(age<3200)for(let i=0;i<2;i++){const snap=Math.max(0,1-(age-2200-i*170)/950);if(snap>0){ctx.save();ctx.globalAlpha=fade*.7;ctx.strokeStyle='#4e942f';ctx.lineWidth=2+i;ctx.beginPath();ctx.moveTo(x-13+i*24,y);ctx.bezierCurveTo(x-22+i*38,y-40*snap,x-6+i*12,y-70*snap,x-10+i*20,y-104*snap);ctx.stroke();ctx.restore();}}
            }
        }
        runPressureEffect(effect,age,offset) {
            const ctx=this.context,s={x:effect.start.x+offset.x,y:effect.start.y+offset.y},end={x:effect.impact.x+offset.x,y:effect.impact.y+offset.y};
            const firing=age>110&&age<1160,fade=age<2800?1:Math.max(0,1-(age-2800)/900);
            if(firing) {
                const burst=Math.min(1,(age-110)/130),cough=age>980?.55+.45*Math.sin(age*.09):1,points=[];
                for(let i=0;i<=22;i++){const t=i/22,wander=Math.sin(age*.018+t*18+effect.phase)*(2+5*t);points.push({x:s.x+(end.x-s.x)*t+wander,y:s.y+(end.y-s.y)*t+Math.sin(t*11+age*.012)*3,r:(3.8+2.5*t)*burst*cough});}
                ctx.save();ctx.shadowColor='#58707166';ctx.shadowBlur=4;this.ribbon(points,'#e9f3df');ctx.restore();
            }
            const mistCount=34;
            for(let i=0;i<mistCount;i++){
                const birth=140+(i%17)*54,elapsed=age-birth;if(elapsed<0||elapsed>1500)continue;
                const t=Math.min(1,elapsed/650),base=i/mistCount,jitter=Math.sin(i*12.7)*25;
                const x=s.x+(end.x-s.x)*t+jitter*t,y=s.y+(end.y-s.y)*t+(i%7-3)*5*t+38*t*t;
                ctx.save();ctx.globalAlpha=fade*Math.max(0,1-elapsed/1500);ctx.fillStyle='#eef6e6';ctx.beginPath();ctx.ellipse(x,y,2+(i%4),1.5+(i%3),0,0,Math.PI*2);ctx.fill();ctx.restore();
            }
            if(age>600){const p=Math.min(1,(age-600)/260);ctx.save();ctx.globalAlpha=fade;ctx.fillStyle='#e4edda';for(let i=0;i<11;i++){ctx.beginPath();ctx.ellipse(end.x+(i-5)*14*p,end.y+(i%3-1)*6,9+(i%4)*3,3+(i%3),-.35,0,Math.PI*2);ctx.fill();}ctx.restore();}
        }
        runBlobCreatureEffect(effect,age,offset) {
            const ctx=this.context,sx=effect.start.x+offset.x,sy=effect.start.y+offset.y,ground=effect.impact.y+offset.y;
            effect.creatures.forEach((creature,index)=>{
                const elapsed=age-creature.birth;if(elapsed<0)return;
                const fallTime=760+index*45,t=Math.min(1,elapsed/fallTime),landed=elapsed>=fallTime;
                const settleAge=Math.max(0,elapsed-fallTime),x=sx+creature.vx*(elapsed/1000),bounce=landed?Math.abs(Math.sin(settleAge*.012))*42*Math.exp(-settleAge/850):0;
                const y=landed?ground-bounce:sy+(ground-sy)*(t*t),impactSquash=landed?Math.max(0,1-settleAge/150):0;
                const vanish=Math.max(0,Math.min(1,(age-5700)/800)),scale=1-vanish;
                if(scale<=0)return;
                const stretch=landed?1-impactSquash*.35:1+Math.min(.28,t*.22),squash=landed?1+impactSquash*.4:1/Math.sqrt(stretch);
                ctx.save();ctx.translate(x,y);ctx.scale(squash*scale,stretch*scale);ctx.shadowColor='#35231455';ctx.shadowBlur=4;ctx.shadowOffsetY=3;
                ctx.fillStyle=creature.colour;ctx.beginPath();ctx.moveTo(-creature.size,2);ctx.bezierCurveTo(-creature.size*1.05,-creature.size*.75,-creature.size*.45,-creature.size*1.08,0,-creature.size*.88);ctx.bezierCurveTo(creature.size*.65,-creature.size*1.15,creature.size*1.08,-creature.size*.55,creature.size,3);ctx.bezierCurveTo(creature.size*.75,creature.size, -creature.size*.78,creature.size,-creature.size,2);ctx.fill();
                const look=creature.look&&settleAge>1000?0:Math.sign(creature.vx)*1.7;
                for(const eyeX of [-creature.size*.34,creature.size*.32]){ctx.fillStyle='white';ctx.beginPath();ctx.ellipse(eyeX,-creature.size*.35,creature.size*.23,creature.size*.29,0,0,Math.PI*2);ctx.fill();ctx.fillStyle='#202018';ctx.beginPath();ctx.arc(eyeX+look,-creature.size*.32,creature.size*.09,0,Math.PI*2);ctx.fill();}
                ctx.restore();
            });
        }
        draw(time) {
            this.frame=0;this.size();const ctx=this.context;
            ctx.clearRect(0,0,root.innerWidth,root.innerHeight);
            this.effects=this.effects.filter(effect=>{
                const alive=time-effect.born<effect.duration;if(!alive)this.active.delete(effect.index);return alive;
            });
            this.effects.forEach(effect=>{
                const age=time-effect.born,offset=this.offset(effect);
                const anchorX=effect.start.x+offset.x,anchorY=effect.start.y+offset.y;
                ctx.save();ctx.translate(anchorX,anchorY);ctx.scale(EFFECT_SCALE,EFFECT_SCALE);ctx.translate(-anchorX,-anchorY);
                if(effect.kind==='cream'){this.puddle(effect,age,offset);this.stream(effect,age,offset);this.droplets(effect,age,offset);}
                else if(effect.kind==='foam')this.runFoamEffect(effect,age,offset);
                else if(effect.kind==='slime')this.runSlimeEffect(effect,age,offset);
                else if(effect.kind==='pressure')this.runPressureEffect(effect,age,offset);
                else if(effect.kind==='creatures')this.runBlobCreatureEffect(effect,age,offset);
                ctx.restore();
            });
            if(this.effects.length)this.frame=requestAnimationFrame(next=>this.draw(next));
            else ctx.clearRect(0,0,root.innerWidth,root.innerHeight);
        }
    }

    class SourceUdder {
        constructor({udder, buttons, layer, reduced=()=>false, raf=fn=>requestAnimationFrame(fn),
                     now=()=>performance.now(), schedule=(fn, ms)=>setTimeout(fn, ms)}) {
            Object.assign(this, {udder, buttons:[...buttons], layer, reduced, raf, now, schedule});
            this.states = this.buttons.map(() => ({position:0, velocity:0, target:0, lastX:null, lastTime:null, frame:false}));
            this.effects=new UdderEffectsCanvas({reduced});
            this.buttons.forEach((button, index) => this.bind(button, index));
        }
        bind(button, index) {
            button.addEventListener('click',event=>{
                if(this.effects.isActive(index)){
                    event.preventDefault();event.stopImmediatePropagation();return;
                }
                this.effects.reserve(index);
            },true);
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
            shape.style.setProperty('--shift', `${(bend*.42).toFixed(2)}px`);
            shape.style.setProperty('--stretch', String(1+Math.min(.12,Math.abs(bend)/190)));
            shape.style.setProperty('--squash', String(1-Math.min(.06,Math.abs(bend)/380)));
        }
        activate(index) {
            const shape=this.buttons[index].querySelector('.teat-shape');
            shape.classList.remove('effect-squeezed');void shape.offsetWidth;shape.classList.add('effect-squeezed');
            this.schedule(()=>shape.classList.remove('effect-squeezed'),220);
            this.effects.start(index,shape);
        }
        splash(teat, colour) {
            const tip=teat.getBoundingClientRect(), parchment=document.querySelector('.profile-container').getBoundingClientRect();
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
