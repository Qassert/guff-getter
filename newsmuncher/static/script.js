let rewriteSequence = 0;
let displayedRewriteId = null;

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
        body: JSON.stringify({ title, description, extract, ...(imagesEnabled ? {generate_images: true} : {}) })
    })
        .then(response => {
            if (!response.ok) throw new Error("Error shizzalising data.");
            return response.json();
        })
        .then(data => {
            if (sequence !== rewriteSequence) return;
            displayedRewriteId = data.rewrite_id || null;
            try {
                if (displayedRewriteId) sessionStorage.setItem('newsmuncher.imageRewrite', displayedRewriteId);
                else sessionStorage.removeItem('newsmuncher.imageRewrite');
            } catch (_) {}
            const titleBox = document.getElementById("crazyTitleBox");
            const extractBox = document.getElementById("crazyExtractBox");

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

function bankThisBeauty() {
    showLoader();
    fetch("/temp/confirm_data" + (displayedRewriteId ? `?rewrite_id=${encodeURIComponent(displayedRewriteId)}` : ""), {
        method: "POST",
        credentials: 'include'
    })
        .then(response => {
            if (!response.ok) throw new Error("Error banking data.");
            return response.json();
        })
        .then(() => {
            alert("Beauty successfully banked!");
            hideLoader();
        })
        .catch(error => {
            console.error("Error banking the beauty:", error);
            hideLoader();
        });
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
        const title = document.getElementById('crazyTitleBox');
        const extract = document.getElementById('crazyExtractBox');
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
