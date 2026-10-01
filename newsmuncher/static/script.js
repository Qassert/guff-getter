let rewriteSequence = 0;
let imageDisplaySequence = 0;
let displayedRewriteId = null;
let nominatedSnapshot = null;
let draftSession = null;
let creationNominated = false, currentImageUrl = null, imageRedoPending = false, imageGenerationFailed = false;
window.creationContext=()=>({rewrite_id:displayedRewriteId,sequence:rewriteSequence});
function renderRedoImage() {
    const button = document.getElementById('redoImageButton');
    if (!button) return;
    button.hidden = creationNominated || (!currentImageUrl && !imageGenerationFailed);
    button.disabled = imageRedoPending || nominationPending;
    const bank = document.getElementById('bankButton');
    if (bank) bank.disabled = imageRedoPending || nominationPending;
    button.textContent = imageRedoPending ? 'REPLACING IMAGE…' : 'REDO IMAGE';
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
        const response = await fetch('/temp/redo_image', {
            method: 'POST', credentials: 'include', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({rewrite_id: id, previous_image_url: previous || null})
        });
        if (!response.ok) throw new Error('Replacement unavailable');
        const data = await response.json();
        if (!current()) return;
        if (typeof imageLoading !== 'undefined') imageLoading.stop(true);
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
    imageRedoPending = !!data.image_redo_pending;
    const redoMessage = document.getElementById('imageRedoMessage');
    if (redoMessage && imageRedoPending) {
        redoMessage.hidden = false;
        redoMessage.textContent = 'Image replacement unresolved. Reload to check saved status; operator review may be needed. No paid retry.';
    }
    renderRedoImage();
    if (typeof videoUI !== "undefined") videoUI.show(data);
    if (typeof narrationUI !== "undefined") narrationUI.show(data);
    if (typeof jingleUI !== "undefined") jingleUI.show(data);
    const button = document.getElementById('bankButton');
    button.textContent = 'NOMINATE';
    button.hidden = data.nominated === true;
    button.disabled = imageRedoPending;
    nominatedSnapshot = data.nominated ? JSON.stringify({
        crazyReplacement1Title: data.crazyReplacement1Title || '',
        crazyReplacement1Extract: data.crazyReplacement1Extract || ''
    }) : null;
}
function responseEdited() {
    if (nominatedSnapshot) document.getElementById('bankButton').textContent = 'UPDATE NOMINATION';
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

function showLoader() {
    document.getElementById("loader").classList.remove("hidden");
}

function hideLoader() {
    document.getElementById("loader").classList.add("hidden");
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
    displayedRewriteId = null;
    nominatedSnapshot = null;
    creationNominated = false;
    nominationPending = false;
    resetImagePanel();
    if (typeof narrationUI !== 'undefined') narrationUI.show({nominated:false});
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
    if (typeof narrationUI !== "undefined") narrationUI.show({nominated: false});
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
            displayedRewriteId = data.rewrite_id || null;
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
                if (typeof narrationUI !== 'undefined') narrationUI.show({nominated: true, rewrite_id: data.rewrite_id || nominatingId});
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
    currentImageUrl = null; imageRedoPending = false; imageGenerationFailed = false;
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
        if (!response.ok) throw new Error('Image generation failed');
        const data = await response.json();
        if (!current()) return;
        if (typeof imageLoading !== 'undefined') imageLoading.stop(true);
        displayRewriteImage(data.image_url, current, data.image_style);

    } catch (error) {
        if (current()) {
            if (typeof imageLoading !== 'undefined') imageLoading.stop();
            imageGenerationFailed = true;
            renderRedoImage();
            panel.textContent = 'Image unavailable. Use REDO IMAGE if you want to make another paid attempt.';
        }
    }
}

window.generateCreationImage=async(id,sequence,replace=false)=>{
 const current=()=>sequence===rewriteSequence&&id===displayedRewriteId;
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
        displayedRewriteId = id;
        setNominationState(data);
        const title=document.getElementById('responseTitleDraft'),extract=document.getElementById('responseBodyDraft');
        title.value=data.crazyReplacement1Title||'';extract.value=data.crazyReplacement1Extract||'';
        document.getElementById('outputContainer').style.display = 'block';
        document.getElementById('bankButton').classList.remove('hidden');
        autoResize(extract);
        if (data.image_url) displayRewriteImage(data.image_url, () => sequence === rewriteSequence && displayedRewriteId === id, data.image_style);
    } catch (_) {} // Restoration is optional and never initiates paid generation.
}

window.onload = () => {
    populateTempData();
    restoreImageRewrite();
    if (typeof jingleUI !== "undefined") jingleUI.discover();
};
