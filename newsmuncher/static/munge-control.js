/* Six independent radial MUNGE teats; native clicks retain the existing handler. */
(function(root) {
    class MungeControl {
        constructor({buttons, reduced=()=>false, raf=fn=>requestAnimationFrame(fn),
                     now=()=>performance.now(), schedule=(fn,ms)=>setTimeout(fn,ms)}={}) {
            this.buttons=[...(buttons || [])]; Object.assign(this,{reduced,raf,now,schedule});
            this.states=this.buttons.map(()=>({position:0,velocity:0,target:0,lastX:null,lastY:null,lastTime:null,frame:false}));
            this.buttons.forEach((button,index)=>this.bind(button,index));
        }
        bind(button,index) {
            button.addEventListener('pointerenter',event=>this.track(index,event));
            button.addEventListener('pointermove',event=>this.flick(index,event));
            button.addEventListener('pointerleave',()=>this.release(index));
            button.addEventListener('pointercancel',()=>this.release(index));
            button.addEventListener('click',()=>this.activate(index));
        }
        track(index,event) {
            if(event.pointerType==='touch'||this.reduced())return;
            Object.assign(this.states[index],{lastX:event.clientX,lastY:event.clientY,lastTime:this.now()});
        }
        flick(index,event) {
            if(event.pointerType==='touch'||this.reduced())return;
            const state=this.states[index],time=this.now(); if(state.lastX===null)return this.track(index,event);
            const elapsed=Math.max(8,time-state.lastTime),dx=event.clientX-state.lastX,dy=event.clientY-state.lastY;
            const speed=Math.min(2.2,Math.hypot(dx,dy)/elapsed);
            const direction=Math.sign(dx+dy)||1; state.target=direction*Math.min(22,4+speed*10); state.velocity+=direction*speed*2.2;
            Object.assign(state,{lastX:event.clientX,lastY:event.clientY,lastTime:time}); this.animate(index);
        }
        release(index) { const state=this.states[index];Object.assign(state,{target:0,lastX:null,lastY:null,lastTime:null});this.animate(index); }
        animate(index) {
            const state=this.states[index];if(state.frame||this.reduced())return;state.frame=true;
            const step=()=>{state.target*=.72;state.velocity+=(state.target-state.position)*.18;state.velocity*=.78;state.position+=state.velocity;this.render(index);
                if(Math.abs(state.position)>.08||Math.abs(state.velocity)>.08||Math.abs(state.target)>.08)this.raf(step);
                else{state.position=state.velocity=state.target=0;state.frame=false;this.render(index);}};this.raf(step);
        }
        render(index) {
            const shape=this.buttons[index].querySelector('.munge-teat-shape'),bend=this.states[index].position;
            const style=this.buttons[index].style,travel=bend*.42;
            const axisX=parseFloat(style.getPropertyValue?.('--axis-x')||style.values?.['--axis-x']||0),axisY=parseFloat(style.getPropertyValue?.('--axis-y')||style.values?.['--axis-y']||0);
            shape.style.setProperty('--bend',`${bend.toFixed(2)}deg`);shape.style.setProperty('--travel-x',`${(travel*axisX).toFixed(2)}px`);shape.style.setProperty('--travel-y',`${(travel*axisY).toFixed(2)}px`);
            shape.style.setProperty('--stretch',String(1+Math.min(.12,Math.abs(bend)/190)));shape.style.setProperty('--squash',String(1-Math.min(.06,Math.abs(bend)/380)));
        }
        activate(index) {
            const shape=this.buttons[index].querySelector('.munge-teat-shape');shape.classList.remove('squeezed');void shape.offsetWidth;shape.classList.add('squeezed');
            this.schedule(()=>shape.classList.remove('squeezed'),260);
        }
    }
    if(typeof module!=='undefined')module.exports={MungeControl};
    if(typeof document==='undefined')return;
    const control=document.getElementById('mungeControl');if(!control)return;
    root.mungeControl=new MungeControl({buttons:control.querySelectorAll('.munge-teat'),reduced:()=>!!root.matchMedia?.('(prefers-reduced-motion: reduce)').matches});
})(typeof globalThis!=='undefined'?globalThis:this);
