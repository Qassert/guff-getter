let rewriteSequence = 0;
let displayedRewriteId = null;
let nominatedSnapshot = null;
let draftSession = null;
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
    const button = document.getElementById('bankButton');
    button.textContent = data.nominated ? 'NOMINATED' : 'NOMINATE';
    button.disabled = false;
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
            const nonsenseBox = document.getElementById("nonsenseBox");
            const titleDescBox = document.getElementById("titleDescBox");

            if (typeof profileEditing !== 'undefined') profileEditing.reset('source');
            nonsenseBox.value = data.extract || "";
            titleDescBox.value = `${data.title || ""} - ${data.description || ""}`.trim();

            autoResize(nonsenseBox);
            document.getElementById("sourceTitleHeading").textContent =
                data.title || data.description ? `...${titleDescBox.value}...` : "";
        })
        .catch(error => {
            console.error("Error populating temporary data:", error);
        });
}

function fetchAndDisplay(scriptName) {
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
                populateTempData();
                hideLoader();
            }, 2000);
        })
        .catch(error => {
            console.error("Error fetching from source:", error);
            hideLoader();
        });
}

function confirmData() {
    const sequence = ++rewriteSequence;
    document.getElementById('bankButton').disabled = true;
    const imagesEnabled = document.getElementById("generateImages").checked;
    resetImagePanel();
    showLoader();
    const title = document.getElementById("titleDescBox").value.split(" - ")[0];
    const description = document.getElementById("titleDescBox").value.split(" - ")[1] || "";
    const extract = document.getElementById("nonsenseBox").value;

    fetch("/temp/shizzalise_data", {
        method: "POST",
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ title, description, extract, draft_session: workingSession(), ...(imagesEnabled ? {generate_images: true} : {}) })
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
            const titleBox = document.getElementById("crazyTitleBox");
            const extractBox = document.getElementById("crazyExtractBox");

            if (typeof profileEditing !== 'undefined') profileEditing.reset('response');
            titleBox.textContent = data.crazyReplacement1Title ? `...${data.crazyReplacement1Title}...` : "";
            extractBox.value = data.crazyReplacement1Extract || "";

            document.getElementById("outputContainer").style.display = 'block';
            document.getElementById("bankButton").classList.remove("hidden");

            // Delay resize until after rendering
            setTimeout(() => {
                autoResize(extractBox);
            }, 0);

            hideLoader();
            if (imagesEnabled && displayedRewriteId) {
                const id = displayedRewriteId;
                // Yield a paint before starting the independent image request.
                requestAnimationFrame(() => requestAnimationFrame(() => {
                    if (sequence === rewriteSequence) loadRewriteImage(id, sequence);
                }));
            }
        })
        .catch(error => {
            if (sequence !== rewriteSequence) return;
            console.error("Error during shizzalise:", error);
            hideLoader();
        });
}

let nominationPending = false;
function bankThisBeauty() {
    if (nominationPending) return;
    const title = document.getElementById('crazyTitleBox').textContent;
    const editor = document.getElementById('responseEditor');
    const response = {
        crazyReplacement1Title: editor && !editor.hidden
            ? document.getElementById('responseTitleDraft').value
            : (title ? title.slice(3, -3) : ''),
        crazyReplacement1Extract: editor && !editor.hidden
            ? document.getElementById('responseBodyDraft').value
            : document.getElementById('crazyExtractBox').value
    };
    const snapshot = JSON.stringify(response);
    if (snapshot === nominatedSnapshot) return;
    nominationPending = true;
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
        .then(() => {
            if (nominatingId === displayedRewriteId && nominatingSequence === rewriteSequence) {
                nominatedSnapshot = snapshot;
                document.getElementById('bankButton').textContent = 'NOMINATED';
            }
            alert("Result nominated (saved for possible promotion).");
            hideLoader();
        })
        .catch(error => {
            console.error("Error banking the beauty:", error);
            hideLoader();
        })
        .finally(() => { nominationPending = false; });
}

function resetImagePanel() {
    const panel = document.getElementById('imagePanel');
    panel.replaceChildren();
    panel.classList.add('hidden');
}

async function loadRewriteImage(id, sequence) {
    const panel = document.getElementById('imagePanel');
    const current = () => sequence === rewriteSequence && id === displayedRewriteId;
    if (!current()) return;
    panel.classList.remove('hidden');
    panel.textContent = 'Putting paint on paper…';
    try {
        const response = await fetch('/temp/generate_image', {
            method: 'POST', credentials: 'include',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({rewrite_id: id})
        });
        if (!response.ok) throw new Error('Image generation failed');
        const data = await response.json();
        if (!current()) return;
        displayRewriteImage(data.image_url, current);

    } catch (error) {
        if (current()) panel.textContent = 'Image unavailable. Your rewrite is ready above.';
    }
}

function displayRewriteImage(url, current) {
    if (!current()) return;
    const panel = document.getElementById('imagePanel');
    const img = new Image();
    img.alt = 'Editorial illustration of the rewritten scene.';
    img.className = 'generated-image';
    img.onload = () => {
        if (!current()) return;
        panel.classList.remove('hidden');
        panel.replaceChildren(img);
        generatedBackground.preload(url, current);
        requestAnimationFrame(() => requestAnimationFrame(() => {
            if (!current()) return;
            img.classList.add('loaded');
            const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            setTimeout(() => {
                if (current()) applyImageColors(img, current);
            }, reduced ? 0 : 650);
        }));
    };
    img.onerror = () => {
        if (current()) panel.textContent = 'Image unavailable. Your rewrite is ready above.';
    };
    img.src = url;
}

async function restoreImageRewrite() {
    let id;
    try { id = sessionStorage.getItem('newsmuncher.imageRewrite'); } catch (_) { return; }
    if (!id) return;
    const sequence = rewriteSequence;
    try {
        const response = await fetch(`/temp/image_result/${encodeURIComponent(id)}`, {credentials: 'include'});
        if (!response.ok) return;
        const data = await response.json();
        if (sequence !== rewriteSequence || data.rewrite_id !== id) return;
        displayedRewriteId = id;
        setNominationState(data);
        const title = document.getElementById('crazyTitleBox');
        const extract = document.getElementById('crazyExtractBox');
        if (typeof profileEditing !== 'undefined') profileEditing.reset('response');
        title.textContent = data.crazyReplacement1Title ? `...${data.crazyReplacement1Title}...` : '';
        extract.value = data.crazyReplacement1Extract || '';
        document.getElementById('outputContainer').style.display = 'block';
        document.getElementById('bankButton').classList.remove('hidden');
        autoResize(extract);
        if (data.image_url) displayRewriteImage(data.image_url, () => sequence === rewriteSequence && displayedRewriteId === id);
    } catch (_) {} // Restoration is optional and never initiates paid generation.
}

window.onload = () => {
    document.getElementById('generateImages').checked = false;
    populateTempData();
    restoreImageRewrite();
};
window.addEventListener('pageshow', () => {
    document.getElementById('generateImages').checked = false;
});
