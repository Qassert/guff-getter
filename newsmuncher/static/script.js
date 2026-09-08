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
            autoResize(titleDescBox);
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
        body: JSON.stringify({ title, description, extract })
    })
        .then(response => {
            if (!response.ok) throw new Error("Error shizzalising data.");
            return response.json();
        })
        .then(data => {
            const titleBox = document.getElementById("crazyTitleBox");
            const extractBox = document.getElementById("crazyExtractBox");

            titleBox.value = data.crazyReplacement1Title || "";
            extractBox.value = data.crazyReplacement1Extract || "";

            document.getElementById("outputContainer").style.display = 'block';
            document.getElementById("bankButton").classList.remove("hidden");

            // Delay resize until after rendering
            setTimeout(() => {
                autoResize(titleBox);
                autoResize(extractBox);
            }, 0);

            hideLoader();
        })
        .catch(error => {
            console.error("Error during shizzalise:", error);
            hideLoader();
        });
}

function bankThisBeauty() {
    showLoader();
    fetch("/temp/confirm_data", {
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

window.onload = populateTempData;
