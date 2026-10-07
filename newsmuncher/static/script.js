let rewriteSequence = 0;
let imageDisplaySequence = 0;
let displayedRewriteId = null;
let nominatedSnapshot = null;
let draftSession = null;
let creationNominated = false, currentImageUrl = null, imageRedoPending = false, imageGenerationFailed = false;
let imageRetryAttemptId = null, imageRetryConfirmation = null;
window.creationContext=()=>({rewrite_id:displayedRewriteId,sequence:rewriteSequence});
function renderRedoImage() {
    const button = document.getElementById('redoImageButton');
    if (!button) return;
    button.hidden = creationNominated || (!currentImageUrl && !imageGenerationFailed);
    button.disabled = imageRedoPending || nominationPending;
    const bank = document.getElementById('bankButton');
    if (bank) bank.disabled = imageRedoPending || nominationPending;
    button.textContent = imageRedoPending ? 'REPLACING IMAGE…' :
        (!currentImageUrl && imageRetryAttemptId ? 'RETRY IMAGE' : 'REDO IMAGE');
}
function confirmUncertainImageRetry() {
    if (!imageRetryAttemptId || imageRetryConfirmation) return Promise.resolve(false);
    const dialog = document.getElementById('imageRetryDialog');
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
    return new Promise(resolve => { imageRetryConfirmation = resolve; });
}
function closeImageRetryDialog(confirmed) {
    const dialog = document.getElementById('imageRetryDialog');
    if (typeof dialog.close === 'function') dialog.close();
    else dialog.removeAttribute('open');
    const resolve = imageRetryConfirmation;
    imageRetryConfirmation = null;
    if (resolve) resolve(confirmed);
}
async function confirmedImageRetry(id, sequence) {
    const attempt = imageRetryAttemptId;
    if (!attempt || !(await confirmUncertainImageRetry())) throw new Error('Image retry cancelled.');
    const response = await fetch('/temp/retry_uncertain_image', {
        method: 'POST', credentials: 'include', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({rewrite_id: id, attempt_id: attempt, confirmed: true})
    });
    if (!response.ok) {
        const failure = await response.json().catch(() => ({}));
        throw new Error(failure.detail || 'Image retry unavailable.');
    }
    if (id !== displayedRewriteId || sequence !== rewriteSequence) throw new Error('Rewrite changed.');
    imageRetryAttemptId = null;
    return response.json();
}
async function redoImage() {
    if (creationNominated || (!currentImageUrl && !imageGenerationFailed) || imageRedoPending || nominationPending) return;
    const id = displayedRewriteId, sequence = rewriteSequence, previous = currentImageUrl;
    const current = () => id === displayedRewriteId && sequence === rewriteSequence;
    if (typeof imageLoading !== 'undefined') imageLoading.start();
    if (typeof videoUI !== 'undefined') videoUI.stop();
    imageRedoPending = true;
    renderRedoImage();
    const message = document.getElementById('imageRedoMessage');
    if (message) { message.hidden = false; message.textContent = 'Generating a replacement image (paid action)…'; }
    try {
        let data;
        if (!previous && imageRetryAttemptId) data = await confirmedImageRetry(id, sequence);
        else {
            const response = await fetch('/temp/redo_image', {
                method: 'POST', credentials: 'include', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({rewrite_id: id, previous_image_url: previous || null})
            });
            if (!response.ok) throw new Error('Replacement unavailable');
            data = await response.json();
        }
        if (!current()) return;
        if (typeof imageLoading !== 'undefined') imageLoading.freeze();
        imageRedoPending = false;
        imageGenerationFailed = false;
        currentImageUrl = data.image_url;
        displayRewriteImage(data.image_url, current, data.image_style);
        if (message) message.hidden = true;
        renderRedoImage();
    } catch (_) {
        if (!current()) return;
        if (typeof imageLoading !== 'undefined') imageLoading.stop();
        // Keep the durable attempt blocked. Restore uses GET and may recover a saved file.
        if (message) message.textContent = 'Replacement uncertain; old image retained. Reload to check saved status. No paid retry.';
    }
}

function workingSession() {
    if (draftSession) return draftSession;
    try { draftSession = sessionStorage.getItem('newsmuncher.draftSession'); } catch (_) {}
    if (!draftSession) {
        draftSession = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        try { sessionStorage.setItem('newsmuncher.draftSession', draftSession); } catch (_) {}
    }
    return draftSession;
}
function setNominationState(data) {
    if (typeof embellishUI !== 'undefined') embellishUI.show(data);
    creationNominated = data.nominated === true;
    currentImageUrl = data.image_url || null;
    imageGenerationFailed = !currentImageUrl && data.image_generation_failed === true;
    imageRetryAttemptId = data.image_outcome_uncertain ? data.image_attempt_id : null;
    imageRedoPending = !!data.image_redo_pending;
    const redoMessage = document.getElementById('imageRedoMessage');
    if (redoMessage && imageRedoPending) {
        redoMessage.hidden = false;
        redoMessage.textContent = 'Image replacement unresolved. Reload to check saved status; operator review may be needed. No paid retry.';
    }
    renderRedoImage();
    if (typeof videoUI !== "undefined") videoUI.show(data);
    if (typeof jingleUI !== "undefined") jingleUI.show(data);
    const button = document.getElementById('bankButton');
    button.textContent = 'NOMINATE';
    button.hidden = data.nominated === true;
    button.disabled = imageRedoPending;
    nominatedSnapshot = data.nominated ? JSON.stringify({
        crazyReplacement1Title: data.crazyReplacement1Title || '',
        crazyReplacement1Extract: data.crazyReplacement1Extract || ''
    }) : null;
    renderDeleteCreation();
}
function renderDeleteCreation() {
    const button = document.getElementById('deleteCreationButton');
    if (button) button.hidden = !displayedRewriteId;
}
function setDisplayedRewriteId(rewriteId) {
    displayedRewriteId = rewriteId || null;
    renderDeleteCreation();
}
function openDeleteCreation() {
    if (!displayedRewriteId) return;
    const dialog = document.getElementById('deleteCreationDialog');
    const error = document.getElementById('deleteCreationError');
    error.hidden = true; error.textContent = '';
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
}
async function deleteCurrentCreation() {
    if (!displayedRewriteId) return;
    const id = displayedRewriteId, sequence = rewriteSequence;
    const confirm = document.getElementById('confirmDeleteCreation');
    const error = document.getElementById('deleteCreationError');
    confirm.disabled = true;
    try {
        const response = await fetch(`/temp/creation/${encodeURIComponent(id)}`, {
            method: 'DELETE', credentials: 'include'
        });
        if (!response.ok) {
            const detail = await response.json().catch(() => ({}));
            throw new Error(detail.detail || 'Creation could not be deleted.');
        }
        if (sequence !== rewriteSequence || id !== displayedRewriteId) return;
        document.getElementById('deleteCreationDialog').close();
        beginNewCreation();
        try { history.replaceState({}, '', window.location.pathname); } catch (_) {}
    } catch (failure) {
        error.textContent = failure.message || 'Creation could not be deleted.';
        error.hidden = false;
    } finally {
        confirm.disabled = false;
    }
}
function responseEdited() {
    if (nominatedSnapshot) document.getElementById('bankButton').textContent = 'UPDATE NOMINATION';
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

let mungeProcessing = false;
let mungeSpinAnimation = null;
let mungeDeceleration = null;
let mungeThrobAnimation = null;
const MUNGE_REVOLUTION_MS = 1120;
const MUNGE_THROB_MS = 1400;
const MUNGE_ANGULAR_VELOCITY = 360 / MUNGE_REVOLUTION_MS;

function mungeRotation(element) {
    const transform = getComputedStyle(element).transform;
    if (!transform || transform === 'none') return 0;
    try {
        const matrix = new DOMMatrixReadOnly(transform);
        return (Math.atan2(matrix.b, matrix.a) * 180 / Math.PI + 360) % 360;
    } catch (_) { return 0; }
}

function finishMungeProcessing(mungeControl, mungeButton) {
    mungeSpinAnimation?.cancel(); mungeSpinAnimation = null;
    mungeDeceleration?.cancel(); mungeDeceleration = null;
    mungeThrobAnimation?.cancel(); mungeThrobAnimation = null;
    mungeControl?.classList.remove('munge-control-processing', 'munge-control-decelerating');
    if (mungeControl) {
        mungeControl.style.transform = '';
        mungeControl.setAttribute('aria-busy', 'false');
    }
    const rotor = document.getElementById('mungeRotor');
    if (rotor) { rotor.style.transform = ''; rotor.style.filter = ''; }
    if (mungeButton) {
        mungeButton.disabled = false;
        mungeButton.setAttribute('aria-disabled', 'false');
    }
    mungeProcessing = false;
}

function setMungeProcessing(running) {
    const mungeControl = document.getElementById('mungeControl');
    const mungeRotor = document.getElementById('mungeRotor');
    const mungeButton = document.getElementById('mungeBodyButton');
    if (!mungeControl || !mungeRotor) return;
    const reduced = !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    if (running) {
        const angle = mungeRotation(mungeRotor);
        mungeDeceleration?.cancel(); mungeDeceleration = null;
        mungeSpinAnimation?.cancel();
        mungeProcessing = true;
        mungeControl.classList.remove('munge-control-decelerating');
        mungeControl.classList.add('munge-control-processing');
        mungeControl.setAttribute('aria-busy', 'true');
        if (mungeButton) {
            mungeButton.disabled = true;
            mungeButton.setAttribute('aria-disabled', 'true');
        }
        if (!reduced) {
            mungeSpinAnimation = mungeRotor.animate(
                [{transform:`rotate(${angle}deg)`},{transform:`rotate(${angle+360}deg)`}],
                {duration:MUNGE_REVOLUTION_MS,iterations:Infinity,easing:'linear'}
            );
            if (mungeThrobAnimation) {
                mungeThrobAnimation.effect.updateTiming({iterations:Infinity});
                mungeThrobAnimation.play();
            } else {
                mungeThrobAnimation = mungeControl.animate([
                    {transform:'scale(1)',offset:0,easing:'cubic-bezier(.45,0,.55,1)'},
                    {transform:'scale(1.5)',offset:.5,easing:'cubic-bezier(.45,0,.55,1)'},
                    {transform:'scale(1)',offset:1}
                ],{duration:MUNGE_THROB_MS,iterations:Infinity});
            }
        }
        return;
    }

    if (!mungeProcessing || mungeDeceleration) return;
    if (reduced) return finishMungeProcessing(mungeControl, mungeButton);

    const angle = mungeRotation(mungeRotor);
    mungeSpinAnimation?.cancel(); mungeSpinAnimation = null;
    mungeControl.classList.remove('munge-control-processing');
    mungeControl.classList.add('munge-control-decelerating');
    const distance = ((360 - angle) % 360) + 360;
    const duration = Math.max(1, (2 * distance) / MUNGE_ANGULAR_VELOCITY);
    const steps = 60;
    const rotationFrames = Array.from({length:steps + 1}, (_, index) => {
        const progress = index / steps;
        const travelled = distance * (2 * progress - progress * progress);
        return {transform:`rotate(${angle + travelled}deg)`,filter:`blur(${1.5 * (1-progress)}px)`,offset:progress};
    });
    mungeDeceleration = mungeRotor.animate(rotationFrames,{duration,easing:'linear',fill:'forwards'});

    let throbFinished = Promise.resolve();
    if (mungeThrobAnimation) {
        const currentTime = Number(mungeThrobAnimation.currentTime) || 0;
        const completedCycles = Math.floor(currentTime / MUNGE_THROB_MS);
        mungeThrobAnimation.effect.updateTiming({iterations:completedCycles + 1});
        throbFinished = mungeThrobAnimation.finished.catch(()=>{});
    }
    Promise.all([mungeDeceleration.finished, throbFinished]).then(()=>{
        if (!mungeDeceleration) return;
        mungeRotor.style.transform='rotate(0deg)';mungeRotor.style.filter='blur(0px)';
        mungeControl.style.transform='scale(1)';
        finishMungeProcessing(mungeControl, mungeButton);
    }).catch(()=>{});
}

function cancelMungeProcessingImmediately() {
    finishMungeProcessing(document.getElementById('mungeControl'), document.getElementById('mungeBodyButton'));
}

function showLoader() {
    document.getElementById("loader").classList.remove("hidden");
    setMungeProcessing(true);
}

function hideLoader() {
    document.getElementById("loader").classList.add("hidden");
    setMungeProcessing(false);
}

function populateTempData() {
    fetch("/temp/temp_data", {
        credentials: 'include'
    })
        .then(response => {
            if (!response.ok) throw new Error("No temporary data found.");
            return response.json();
        })
        .then(data => {
            const title=document.getElementById('sourceTitleDraft'),body=document.getElementById('sourceBodyDraft');
            title.value=[data.title,data.description].filter(Boolean).join(' - ');body.value=data.extract||'';
            autoResize(title);autoResize(body);
        })
        .catch(error => {
            console.error("Error populating temporary data:", error);
        });
}

function fetchAndDisplay(scriptName) {
    const sourceSequence = beginNewCreation();
    document.querySelectorAll('.source-choice').forEach(button => {
        button.setAttribute('aria-pressed', String(button.dataset.source === scriptName));
    });
    showLoader();
    fetch(`/temp/run_script/${scriptName}`, {
        credentials: 'include'
    })
        .then(response => response.json())
        .then(() => {
            setTimeout(() => {
                if (sourceSequence !== rewriteSequence) return;
                populateTempData();
                hideLoader();
            }, 2000);
        })
        .catch(error => {
            console.error("Error fetching from source:", error);
            if (sourceSequence === rewriteSequence) hideLoader();
        });
}

function beginNewCreation() {
    rewriteSequence++;
    setDisplayedRewriteId(null);
    nominatedSnapshot = null;
    creationNominated = false;
    nominationPending = false;
    resetImagePanel();
    if (typeof jingleUI !== 'undefined') jingleUI.show({nominated:false});
    if (typeof embellishUI !== 'undefined') embellishUI.show(null);
    document.getElementById('responseTitleDraft').value = '';
    document.getElementById('responseBodyDraft').value = '';
    const output = document.getElementById('outputContainer');
    output.style.display = 'none';
    output.classList.add('hidden');
    document.getElementById('bankButton').hidden = true;
    try { sessionStorage.removeItem('newsmuncher.imageRewrite'); } catch (_) {}
    return rewriteSequence;
}

function confirmData() {
    if (mungeProcessing) return;
    if (typeof jingleUI !== "undefined") jingleUI.show({nominated: false});
    const sequence = ++rewriteSequence;
    document.getElementById('bankButton').disabled = true;
    resetImagePanel();
    showLoader();
    const sourceTitle=document.getElementById('sourceTitleDraft').value,[title,...parts]=sourceTitle.split(' - ');
    const description=parts.join(' - '),extract=document.getElementById('sourceBodyDraft').value;

    fetch("/temp/shizzalise_data", {
        method: "POST",
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({title,description,extract,draft_session:workingSession()})
    })
        .then(response => {
            if (!response.ok) throw new Error("Error shizzalising data.");
            return response.json();
        })
        .then(data => {
            if (sequence !== rewriteSequence) return;
            setDisplayedRewriteId(data.rewrite_id);
            setNominationState(data);
            try {
                if (displayedRewriteId) sessionStorage.setItem('newsmuncher.imageRewrite', displayedRewriteId);
                else sessionStorage.removeItem('newsmuncher.imageRewrite');
            } catch (_) {}
            const titleBox=document.getElementById('responseTitleDraft'),extractBox=document.getElementById('responseBodyDraft');
            titleBox.value=data.crazyReplacement1Title||'';extractBox.value=data.crazyReplacement1Extract||'';

            document.getElementById("outputContainer").style.display = 'block';
            document.getElementById("bankButton").classList.remove("hidden");

            // Delay resize until after rendering
            setTimeout(() => {
                autoResize(extractBox);
            }, 0);

            hideLoader();
        })
        .catch(error => {
            if (sequence !== rewriteSequence) return;
            console.error("Error during shizzalise:", error);
            hideLoader();
        });
}

let nominationPending = false;
function currentResultText() {
    return {
        crazyReplacement1Title: document.getElementById('responseTitleDraft').value,
        crazyReplacement1Extract: document.getElementById('responseBodyDraft').value
    };
}

window.persistCreationText = async () => {
    if (!displayedRewriteId || !creationNominated) throw new Error('Nomination unavailable.');
    const text = currentResultText();
    const response = await fetch(`/temp/confirm_data?rewrite_id=${encodeURIComponent(displayedRewriteId)}`, {
        method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},
        body:JSON.stringify(text)
    });
    if (!response.ok) throw new Error('Could not update nominated response.');
    nominatedSnapshot = JSON.stringify(text);
    return {rewrite_id:displayedRewriteId, text};
};

function bankThisBeauty() {
    if (nominationPending || imageRedoPending) return;
    const response = currentResultText();
    const snapshot = JSON.stringify(response);
    if (snapshot === nominatedSnapshot) return;
    nominationPending = true;
    renderRedoImage();
    const nominatingId = displayedRewriteId;
    const nominatingSequence = rewriteSequence;
    showLoader();
    fetch("/temp/confirm_data" + (displayedRewriteId ? `?rewrite_id=${encodeURIComponent(displayedRewriteId)}` : ""), {
        method: "POST",
        credentials: 'include',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(response)
    })
        .then(response => {
            if (!response.ok) throw new Error("Error banking data.");
            return response.json();
        })
        .then(data => {
            if (data.nominated !== true) throw new Error('Nomination was not confirmed.');
            if (nominatingId === displayedRewriteId && nominatingSequence === rewriteSequence) {
                if (typeof embellishUI !== 'undefined') embellishUI.show({nominated:true,rewrite_id:data.rewrite_id || nominatingId});
                creationNominated = data.nominated === true;
                renderRedoImage();
                if (typeof videoUI !== 'undefined') videoUI.show({nominated: creationNominated, rewrite_id: data.rewrite_id || nominatingId});
                nominatedSnapshot = snapshot;
                document.getElementById('bankButton').hidden=true;
                if (typeof jingleUI !== 'undefined') jingleUI.show({nominated: true, rewrite_id: data.rewrite_id || nominatingId});
                if(typeof embellishUI!=='undefined')embellishUI.nominate({rewrite_id:data.rewrite_id||nominatingId,sequence:nominatingSequence});
            }
            if (typeof jingleUI !== 'undefined') jingleUI.discover();
        })
        .catch(error => {
            console.error("Error banking the beauty:", error);
            hideLoader();
        })
        .finally(() => { nominationPending = false; renderRedoImage(); });
}

function setImageStyle(style) {
    const label = document.getElementById('imageStyle');
    if (label) {
        label.textContent = style ? `IMAGE STYLE: ${style.toUpperCase()}` : '';
        label.hidden = !style;
    }
    if (typeof creationMeta !== 'undefined') creationMeta.setStyle(style || '');
}

function resetImagePanel() {
    if (typeof imageLoading !== 'undefined') imageLoading.stop();
    if (typeof embellishUI !== 'undefined') embellishUI.show(null);
    if (typeof creationMeta !== 'undefined') creationMeta.reset();
    imageDisplaySequence++;
    setImageStyle(null);
    currentImageUrl = null; imageRedoPending = false; imageGenerationFailed = false; imageRetryAttemptId = null;
    renderRedoImage();
    const message = document.getElementById('imageRedoMessage');
    if (message) message.hidden = true;
    if (typeof videoUI !== "undefined") videoUI.show(null);
    const panel = document.getElementById('imagePanel');
    panel.replaceChildren();
    panel.classList.add('hidden');
}

async function loadRewriteImage(id, sequence) {
    const panel = document.getElementById('imagePanel');
    const current = () => sequence === rewriteSequence && id === displayedRewriteId;
    if (!current()) return;
    panel.classList.remove('hidden');
    panel.textContent = '';
    if (typeof imageLoading !== 'undefined') imageLoading.start();
    try {
        const response = await fetch('/temp/generate_image', {
            method: 'POST', credentials: 'include',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({rewrite_id: id})
        });
        if (!response.ok) {
            const failure = await response.json().catch(() => ({}));
            if (failure.detail?.code === 'image_outcome_uncertain') {
                imageRetryAttemptId = failure.detail.attempt_id || null;
            }
            throw new Error(failure.detail?.message || failure.detail || 'Image generation failed');
        }
        const data = await response.json();
        if (!current()) return;
        if (typeof imageLoading !== 'undefined') imageLoading.freeze();
        displayRewriteImage(data.image_url, current, data.image_style);

    } catch (error) {
        if (current()) {
            if (typeof imageLoading !== 'undefined') imageLoading.stop();
            imageGenerationFailed = true;
            renderRedoImage();
            panel.textContent = imageRetryAttemptId
                ? 'Previous image generation had an uncertain outcome. Use RETRY IMAGE to review a paid retry.'
                : 'Image unavailable. Use REDO IMAGE if you want to make another paid attempt.';
        }
    }
}

window.generateCreationImage=async(id,sequence,replace=false)=>{
 const current=()=>sequence===rewriteSequence&&id===displayedRewriteId;
 if(replace&&!currentImageUrl&&imageRetryAttemptId){const data=await confirmedImageRetry(id,sequence);return{data,reveal(){currentImageUrl=data.image_url;return displayRewriteImage(data.image_url,current,data.image_style);}};}
 const url=replace?'/temp/redo_image':'/temp/generate_image';
 const body=replace?{rewrite_id:id,previous_image_url:currentImageUrl,replace_nomination:true}:{rewrite_id:id};
 const response=await fetch(url,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 if(!response.ok)throw Error('Image generation failed');const data=await response.json();if(!current())throw Error('Rewrite changed');
 return{data,reveal(){currentImageUrl=data.image_url;return displayRewriteImage(data.image_url,current,data.image_style);}};
};

function displayRewriteImage(url, current, style = null) {
    if (!current()) return Promise.resolve(false);
    return new Promise(resolve => {
    const rewriteCurrent = current, imageToken = ++imageDisplaySequence;
    current = () => rewriteCurrent() && imageToken === imageDisplaySequence;
    if (typeof videoUI !== "undefined") videoUI.show({rewrite_id: displayedRewriteId, nominated: creationNominated});
    const panel = document.getElementById('imagePanel');
    if (!currentImageUrl) setImageStyle(null);
    const img = new Image();
    img.alt = 'Editorial illustration of the rewritten scene.';
    img.className = 'generated-image';
    img.onload = () => {
        if (!current()) return;
        if (typeof imageLoading !== 'undefined') imageLoading.stop();
        panel.classList.remove('hidden');
        panel.replaceChildren(img);
        setImageStyle(style);
        currentImageUrl = url;
        renderRedoImage();
        generatedBackground.preload(url, current);
        requestAnimationFrame(() => requestAnimationFrame(() => {
            if (!current()) return;
            img.classList.add('loaded');
            if (typeof videoUI !== 'undefined') videoUI.imageReady();
            const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            setTimeout(() => {
                if (current()) applyImageColors(img, current);
            }, reduced ? 0 : 650);
            resolve(true);
        }));
    };
    img.onerror = () => {
        if (current()) {
            if (typeof imageLoading !== 'undefined') imageLoading.stop();
            imageGenerationFailed = true;
            renderRedoImage();
            panel.textContent = 'Image unavailable. Use REDO IMAGE if you want to make another paid attempt.';
            resolve(false);
        }
    };
    img.src = url;
    });
}

async function restoreImageRewrite() {
    let id;
    try { id = new URLSearchParams(window.location.search).get('rewrite_id'); } catch (_) {}
    try {
        id = id || sessionStorage.getItem('newsmuncher.imageRewrite');
        if (id) sessionStorage.setItem('newsmuncher.imageRewrite', id);
    } catch (_) { if (!id) return; }
    if (!id) return;
    const sequence = rewriteSequence;
    try {
        const response = await fetch(`/temp/image_result/${encodeURIComponent(id)}`, {credentials: 'include'});
        if (!response.ok) return;
        const data = await response.json();
        if (sequence !== rewriteSequence || data.rewrite_id !== id) return;
        setDisplayedRewriteId(id);
        setNominationState(data);
        const title=document.getElementById('responseTitleDraft'),extract=document.getElementById('responseBodyDraft');
        title.value=data.crazyReplacement1Title||'';extract.value=data.crazyReplacement1Extract||'';
        document.getElementById('outputContainer').style.display = 'block';
        document.getElementById('bankButton').classList.remove('hidden');
        autoResize(extract);
        if (data.image_url) displayRewriteImage(data.image_url, () => sequence === rewriteSequence && displayedRewriteId === id, data.image_style);
    } catch (_) {} // Restoration is optional and never initiates paid generation.
}

document.getElementById('mungeControl')?.querySelectorAll?.('.munge-teat, .munge-body-button')?.forEach(button => button.addEventListener('click', confirmData));
window.addEventListener('pagehide', cancelMungeProcessingImmediately);
document.getElementById('deleteCreationButton')?.addEventListener('click', openDeleteCreation);
document.getElementById('confirmDeleteCreation')?.addEventListener('click', deleteCurrentCreation);
document.getElementById('cancelDeleteCreation')?.addEventListener('click', () => {
    const dialog = document.getElementById('deleteCreationDialog');
    if (typeof dialog.close === 'function') dialog.close();
    else dialog.removeAttribute('open');
});
document.getElementById('confirmImageRetry')?.addEventListener('click', () => closeImageRetryDialog(true));
document.getElementById('cancelImageRetry')?.addEventListener('click', () => closeImageRetryDialog(false));
document.getElementById('imageRetryDialog')?.addEventListener('cancel', event => {
    event.preventDefault(); closeImageRetryDialog(false);
});
window.addEventListener('pageshow', renderDeleteCreation);

window.onload = () => {
    populateTempData();
    restoreImageRewrite();
    if (typeof jingleUI !== "undefined") jingleUI.discover();
};
