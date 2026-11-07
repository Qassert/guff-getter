let rewriteSequence = 0;
let imageDisplaySequence = 0;
let displayedRewriteId = null;
let nominatedSnapshot = null;
let draftSession = null;
let creationNominated = false, currentImageUrl = null, imageRedoPending = false, imageGenerationFailed = false;
let imageRetryAttemptId = null, imageRetryConfirmation = null;
let sourceLoading = false;
const BUILD_IMAGE_REJECTION_GUIDANCE = "The image generator doesn't like your text, maybe there is something naughty in there? A Little Hack: You can replace those words by editing them, replacing them for something less naughty but equally descriptive! Then hit Redo image, and it might work, then you can put naughties back in after";
window.creationContext=()=>({rewrite_id:displayedRewriteId,sequence:rewriteSequence});
function showImageFailure(message, rejected = false) {
    const panel = document.getElementById('imagePanel');
    if (!panel) return;
    panel.replaceChildren();
    panel.classList.remove('hidden');
    panel.classList.toggle('image-generation-rejected', rejected);
    const copy = document.createElement('p');
    copy.className = 'image-failure-copy';
    copy.textContent = message;
    panel.appendChild(copy);
}
function renderRedoImage() {
    renderNominationButton();
    const button = document.getElementById('redoImageButton');
    if (!button) return;
    // Successful images are replaced only through RE-EMBELLISH. This explicit
    // recovery action is for a failed image attempt, nominated or otherwise.
    button.hidden = !imageGenerationFailed;
    button.disabled = imageRedoPending || nominationPending;
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
    if (!imageGenerationFailed || imageRedoPending || nominationPending) return;
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
                body: JSON.stringify({rewrite_id: id, previous_image_url: previous || null,
                                      replace_nomination: creationNominated})
            });
            if (!response.ok) {
                const failure = await response.json().catch(() => ({}));
                const error = new Error(failure.detail || 'Replacement unavailable');
                error.definitive = response.status === 422;
                throw error;
            }
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
    } catch (error) {
        if (!current()) return;
        if (typeof imageLoading !== 'undefined') imageLoading.stop();
        if (error.definitive) {
            imageRedoPending = false;
            imageGenerationFailed = true;
            renderRedoImage();
            if (message) message.textContent = 'Image was rejected. Use REDO IMAGE to make another explicit attempt.';
        } else {
            // Keep an ambiguous durable attempt blocked. Restore uses GET and may
            // recover a saved file without making another paid request.
            if (message) message.textContent = 'Replacement uncertain; old image retained. Reload to check saved status. No paid retry.';
        }
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
    nominatedSnapshot = data.nominated ? JSON.stringify({
        crazyReplacement1Title: data.crazyReplacement1Title || '',
        crazyReplacement1Extract: data.crazyReplacement1Extract || ''
    }) : null;
    renderNominationButton();
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
    renderNominationButton();
}

function renderNominationButton() {
    const button = document.getElementById('bankButton');
    if (!button) return;
    const current = typeof currentResultText === 'function'
        ? JSON.stringify(currentResultText()) : null;
    const changed = !!nominatedSnapshot && current !== nominatedSnapshot;
    button.hidden = !displayedRewriteId;
    button.textContent = creationNominated
        ? (changed ? 'UPDATE NOMINATION' : 'NOMINATED') : 'NOMINATE';
    button.disabled = nominationPending || imageRedoPending ||
        (creationNominated && !changed);
}

let copyFeedbackTimer = null;
function updateCopyButton() {
    const button = document.getElementById('copyMungeButton');
    const text = document.getElementById('responseBodyDraft')?.value || '';
    if (!button) return;
    button.hidden = !text;
    button.disabled = !text;
}

async function copyMungeResult() {
    const button = document.getElementById('copyMungeButton');
    const text = document.getElementById('responseBodyDraft')?.value || '';
    if (!button || !text) return;
    clearTimeout(copyFeedbackTimer);
    try {
        await navigator.clipboard.writeText(text);
        button.textContent = 'COPIED!';
    } catch (_) {
        button.textContent = 'COPY FAILED';
    }
    copyFeedbackTimer = setTimeout(() => {
        button.textContent = 'COPY';
        updateCopyButton();
    }, 1600);
}

function autoResize(textarea) {
    if (textarea?.id === 'responseBodyDraft' && responseArticleFitter) {
        responseArticleFitter.schedule();
        return;
    }
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

const responseArticleFitter = typeof ArticleTextFitter === 'function' &&
    document.getElementById('responseBodyDraft') && document.getElementById('responseEditor')
    ? new ArticleTextFitter({
        element: document.getElementById('responseBodyDraft'),
        container: document.getElementById('responseEditor')
    })
        .observe(document.getElementById('responseEditor'))
        .observe(document.getElementById('outputContainer'))
        .observe(document.getElementById('imagePanel'))
    : null;

let mungeProcessing = false;
let mungeSpinAnimations = [];
let mungeDecelerations = [];
const MUNGE_REVOLUTION_MS = 2240;
const MUNGE_QUARTER_TURN_MS = MUNGE_REVOLUTION_MS / 4;
const MUNGE_HALF_TURN_MS = MUNGE_REVOLUTION_MS / 2;
const MUNGE_ANGULAR_VELOCITY = 360 / MUNGE_REVOLUTION_MS;

function mungeRotation(element) {
    const transform = getComputedStyle(element).transform;
    if (!transform || transform === 'none') return 0;
    try {
        const matrix = new DOMMatrixReadOnly(transform);
        return (Math.atan2(matrix.b, matrix.a) * 180 / Math.PI + 360) % 360;
    } catch (_) { return 0; }
}

function mungeEngineForRotor(rotor) {
    return rotor.closest?.('.munge-control')?.dataset?.mungeEngine || rotor.id?.replace('mungeRotor-', '') || 'current';
}

function startMiddleMungeMotion(rotor) {
    let cancelled = false;
    let active = rotor.animate(
        [{transform:'rotate(0deg)'},{transform:'rotate(-90deg)'}],
        {duration:MUNGE_QUARTER_TURN_MS,easing:'linear',fill:'forwards'}
    );
    const intro = active;
    intro.finished.then(() => {
        if (cancelled || !mungeProcessing) return;
        active = rotor.animate(
            [{transform:'rotate(-90deg)'},{transform:'rotate(90deg)'}],
            {duration:MUNGE_HALF_TURN_MS,iterations:Infinity,direction:'alternate',easing:'linear'}
        );
    }).catch(()=>{});
    return {cancel() { cancelled = true; active?.cancel(); if (active !== intro) intro.cancel(); }};
}

function startMungeRotorMotion(rotor) {
    const engine = mungeEngineForRotor(rotor);
    if (engine === 'current') return startMiddleMungeMotion(rotor);
    const start = mungeRotation(rotor);
    const turn = engine === 'classic' ? -360 : 360;
    return rotor.animate(
        [{transform:`rotate(${start}deg)`},{transform:`rotate(${start+turn}deg)`}],
        {duration:MUNGE_REVOLUTION_MS,iterations:Infinity,easing:'linear'}
    );
}

function finishMungeProcessing() {
    mungeSpinAnimations.forEach(animation => animation?.cancel()); mungeSpinAnimations = [];
    mungeDecelerations.forEach(animation => animation?.cancel()); mungeDecelerations = [];
    document.querySelectorAll('.munge-control').forEach(control => {
        control.classList.remove('munge-control-processing', 'munge-control-decelerating');
        control.style.transform = ''; control.setAttribute('aria-busy', 'false');
    });
    document.querySelectorAll('.munge-rotor').forEach(rotor => {
        rotor.style.transform = ''; rotor.style.filter = '';
    });
    document.querySelectorAll('.munge-body-button').forEach(button => {
        button.disabled = false; button.setAttribute('aria-disabled', 'false');
    });
    mungeProcessing = false;
}

function setMungeProcessing(running) {
    const controls = [...document.querySelectorAll('.munge-control')];
    const rotors = [...document.querySelectorAll('.munge-rotor')];
    if (!controls.length || !rotors.length) return;
    const reduced = !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    if (running) {
        mungeDecelerations.forEach(animation => animation?.cancel()); mungeDecelerations = [];
        mungeSpinAnimations.forEach(animation => animation?.cancel());
        mungeProcessing = true;
        controls.forEach(control => {
            control.classList.remove('munge-control-decelerating');
            control.classList.add('munge-control-processing'); control.setAttribute('aria-busy', 'true');
        });
        document.querySelectorAll('.munge-body-button').forEach(button => {
            button.disabled = true; button.setAttribute('aria-disabled', 'true');
        });
        if (!reduced) {
            mungeSpinAnimations = rotors.map(startMungeRotorMotion);
        }
        return;
    }

    if (!mungeProcessing || mungeDecelerations.length) return;
    if (reduced) return finishMungeProcessing();
    mungeSpinAnimations.forEach(animation => animation?.cancel()); mungeSpinAnimations = [];
    controls.forEach(control => {
        control.classList.remove('munge-control-processing'); control.classList.add('munge-control-decelerating');
    });
    mungeDecelerations = rotors.map(rotor => {
        const angle=mungeRotation(rotor),distance=((360-angle)%360)+360;
        return rotor.animate([{transform:`rotate(${angle}deg)`},{transform:`rotate(${angle+distance}deg)`}],
            {duration:Math.max(1,(2*distance)/MUNGE_ANGULAR_VELOCITY),easing:'ease-out',fill:'forwards'});
    });
    Promise.all(mungeDecelerations.map(animation => animation.finished)).then(finishMungeProcessing).catch(()=>{});
}

function cancelMungeProcessingImmediately() {
    window.mungeMusic?.stop();
    finishMungeProcessing();
}

function showLoader() {
    document.getElementById("loader").classList.remove("hidden");
    setMungeProcessing(true);
}

function hideLoader() {
    document.getElementById("loader").classList.add("hidden");
    setMungeProcessing(false);
}

async function populateTempData(sourceSequence = rewriteSequence) {
    const response = await fetch("/temp/temp_data", {credentials:'include'});
    if (!response.ok) throw new Error("No temporary data found.");
    const data = await response.json();
    if (sourceSequence !== rewriteSequence) return false;
    const title=document.getElementById('sourceTitleDraft'),body=document.getElementById('sourceBodyDraft');
    const url=document.getElementById('sourceUrlDraft'),name=document.getElementById('sourceNameDraft');
    const author=document.getElementById('sourceAuthorDraft'),licence=document.getElementById('sourceLicenceDraft');
    const attribution=document.getElementById('sourceAttribution');
    title.value=[data.title,data.description].filter(Boolean).join(' - ');body.value=data.extract||'';
    if(url)url.value=data.source_url||'';if(name)name.value=data.source_name||'';
    if(author)author.value=data.source_author||'';if(licence)licence.value=data.source_licence||'';
    if(attribution){
        attribution.href=data.source_url||'';
        const credit=data.source_author?`${data.source_name||'Source'} — ${data.source_author}`:(data.source_name||data.source_url);
        attribution.textContent=data.source_url?`Source: ${credit}`:'';
        attribution.hidden=!data.source_url;
    }
    autoResize(title);autoResize(body);
    return true;
}

function setSourceLoading(running) {
    sourceLoading=running;
    document.querySelectorAll('.source-choice').forEach(button=>{
        button.disabled=running;button.setAttribute('aria-disabled',String(running));
    });
    document.querySelector('.nonsense-container')?.setAttribute('aria-busy',String(running));
}

async function fetchAndDisplay(scriptName) {
    if(sourceLoading)return;
    const sourceSequence = beginNewCreation();
    document.querySelectorAll('.source-choice').forEach(button => {
        button.setAttribute('aria-pressed', String(button.dataset.source === scriptName));
    });
    setSourceLoading(true);showLoader();
    const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),35000);
    try {
        const response=await fetch(`/temp/run_script/${scriptName}`,{
            credentials:'include',signal:controller.signal
        });
        const result=await response.json().catch(()=>({}));
        if(!response.ok)throw new Error(result.detail||`Source request failed (${response.status}).`);
        await populateTempData(sourceSequence);
    }catch(error){
        console.error("Error fetching from source:",error);
    }finally{
        clearTimeout(timeout);
        if(sourceSequence===rewriteSequence)hideLoader();
        setSourceLoading(false);
    }
}

function beginNewCreation() {
    window.mungeMusic?.stop();
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
    const sourceUrl=document.getElementById('sourceUrlDraft'),sourceName=document.getElementById('sourceNameDraft');
    const sourceAuthor=document.getElementById('sourceAuthorDraft'),sourceLicence=document.getElementById('sourceLicenceDraft');
    const sourceAttribution=document.getElementById('sourceAttribution');
    if(sourceUrl)sourceUrl.value='';if(sourceName)sourceName.value='';
    if(sourceAuthor)sourceAuthor.value='';if(sourceLicence)sourceLicence.value='';
    if(sourceAttribution){sourceAttribution.hidden=true;sourceAttribution.href='';sourceAttribution.textContent='';}
    updateCopyButton();
    const output = document.getElementById('outputContainer');
    output.style.display = 'none';
    output.classList.add('hidden');
    document.getElementById('bankButton').hidden = true;
    try { sessionStorage.removeItem('newsmuncher.imageRewrite'); } catch (_) {}
    return rewriteSequence;
}

function resetCreationActionState() {
    rewriteSequence++;
    setDisplayedRewriteId(null);
    nominatedSnapshot = null;
    creationNominated = false;
    nominationPending = false;
    resetImagePanel();
    if (typeof jingleUI !== 'undefined') jingleUI.show({nominated:false});
    renderNominationButton();
    updateCopyButton();
}

function attachCreationDraft(data) {
    setDisplayedRewriteId(data.rewrite_id);
    creationNominated = false;
    nominatedSnapshot = null;
    const title = document.getElementById('responseTitleDraft');
    const body = document.getElementById('responseBodyDraft');
    if (title) title.value = data.crazyReplacement1Title || '';
    if (body && data.crazyReplacement1Extract != null) body.value = data.crazyReplacement1Extract;
    renderNominationButton();
    updateCopyButton();
}

window.creationActions = {
    reset: resetCreationActionState,
    attachDraft: attachCreationDraft,
    hasDraft: () => Boolean(displayedRewriteId),
    nominate: () => bankThisBeauty(),
};

function confirmData(event) {
    if (mungeProcessing) return;
    const mungeClickedAt = window.performance?.now?.() ?? Date.now();
    const mungeMessage = document.getElementById('mungeMessage');
    if (mungeMessage) { mungeMessage.hidden = true; mungeMessage.textContent = ''; }
    if (typeof jingleUI !== "undefined") jingleUI.show({nominated: false});
    const sequence = ++rewriteSequence;
    document.getElementById('bankButton').disabled = true;
    resetImagePanel();
    window.mungeMusic?.start(mungeClickedAt);
    showLoader();
    const sourceTitle=document.getElementById('sourceTitleDraft').value,[title,...parts]=sourceTitle.split(' - ');
    const description=parts.join(' - '),extract=document.getElementById('sourceBodyDraft').value;
    const source_url=document.getElementById('sourceUrlDraft')?.value||null;
    const source_name=document.getElementById('sourceNameDraft')?.value||null;
    const source_author=document.getElementById('sourceAuthorDraft')?.value||null;
    const source_licence=document.getElementById('sourceLicenceDraft')?.value||null;

    const engine = event?.currentTarget?.dataset?.mungeEngine || 'current';
    window.mungeMusic?.markApiDispatched();
    fetch("/temp/shizzalise_data", {
        method: "POST",
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({title,description,extract,source_url,source_name,source_author,source_licence,draft_session:workingSession(),engine})
    })
        .then(async response => {
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.detail || "Could not create this MUNGE. Please try again.");
            return data;
        })
        .then(data => {
            if (sequence !== rewriteSequence) return;
            window.mungeMusic?.stop();
            setDisplayedRewriteId(data.rewrite_id);
            setNominationState(data);
            try {
                if (displayedRewriteId) sessionStorage.setItem('newsmuncher.imageRewrite', displayedRewriteId);
                else sessionStorage.removeItem('newsmuncher.imageRewrite');
            } catch (_) {}
            const titleBox=document.getElementById('responseTitleDraft'),extractBox=document.getElementById('responseBodyDraft');
            titleBox.value=data.crazyReplacement1Title||'';extractBox.value=data.crazyReplacement1Extract||'';
            updateCopyButton();

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
            window.mungeMusic?.stop();
            console.error("Error during shizzalise:", error);
            if (mungeMessage) {
                mungeMessage.textContent = error.message;
                mungeMessage.hidden = false;
            }
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
    renderNominationButton();
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
                const savedText = {
                    crazyReplacement1Title: data.crazyReplacement1Title ?? response.crazyReplacement1Title,
                    crazyReplacement1Extract: data.crazyReplacement1Extract ?? response.crazyReplacement1Extract
                };
                document.getElementById('responseTitleDraft').value = savedText.crazyReplacement1Title;
                document.getElementById('responseBodyDraft').value = savedText.crazyReplacement1Extract;
                currentImageUrl = data.image_url || null;
                if (typeof embellishUI !== 'undefined') embellishUI.show({nominated:true,rewrite_id:data.rewrite_id || nominatingId});
                creationNominated = data.nominated === true;
                renderRedoImage();
                if (typeof videoUI !== 'undefined') videoUI.show({nominated: creationNominated, rewrite_id: data.rewrite_id || nominatingId});
                nominatedSnapshot = JSON.stringify(savedText);
                renderNominationButton();
                if (typeof jingleUI !== 'undefined') jingleUI.show({nominated: true, rewrite_id: data.rewrite_id || nominatingId});
                if(typeof embellishUI!=='undefined')embellishUI.nominate({rewrite_id:data.rewrite_id||nominatingId,sequence:nominatingSequence});
            }
            if (typeof jingleUI !== 'undefined') jingleUI.discover();
        })
        .catch(error => {
            console.error("Error banking the beauty:", error);
            hideLoader();
        })
        .finally(() => {
            nominationPending = false;
            renderRedoImage();
            renderNominationButton();
        });
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
    panel.classList.remove('image-generation-rejected');
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
 if(!response.ok){
  const failure=await response.json().catch(()=>({}));
  if(current()){
   imageGenerationFailed=true;
   imageRetryAttemptId=failure.detail?.code==='image_outcome_uncertain'?(failure.detail.attempt_id||null):null;
   renderRedoImage();
   if(response.status===422&&document.body.classList.contains('build-page'))showImageFailure(BUILD_IMAGE_REJECTION_GUIDANCE,true);
  }
  throw Error(failure.detail?.message||failure.detail||'Image generation failed');
 }
 const data=await response.json();if(!current())throw Error('Rewrite changed');
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
        panel.classList.remove('image-generation-rejected');
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
        renderNominationButton();
        document.getElementById('outputContainer').style.display = 'block';
        document.getElementById('bankButton').classList.remove('hidden');
        autoResize(extract);
        if (data.image_url) displayRewriteImage(data.image_url, () => sequence === rewriteSequence && displayedRewriteId === id, data.image_style);
    } catch (_) {} // Restoration is optional and never initiates paid generation.
}

document.getElementById('mungeControls')?.querySelectorAll?.('.munge-teat, .munge-body-button')?.forEach(button => button.addEventListener('click', confirmData));
window.addEventListener('pagehide', () => {
    cancelMungeProcessingImmediately();
    responseArticleFitter?.disconnect();
});
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
    if (document.getElementById('sourceBodyDraft')) {
        populateTempData().catch(error=>console.error("Error populating temporary data:",error));
    }
    if (!document.querySelector('[data-build-workshop]')) restoreImageRewrite();
    if (typeof jingleUI !== "undefined") jingleUI.discover();
};
