/* Page-local grouped drafts: no requests from Edit/Save/Cancel. */
const profileEditing = (() => {
    const groups = {
        source: {title: 'sourceTitleHeading', body: 'nonsenseBox'},
        response: {title: 'crazyTitleBox', body: 'crazyExtractBox'}
    };
    const get = id => document.getElementById(id);
    function close(key, focus) {
        get(key + 'Display').hidden = false;
        get(key + 'Editor').hidden = true;
        get(key + 'Edit').setAttribute('aria-expanded', 'false');
        if (focus) get(key + 'Edit').focus();
    }
    return {
        edit(key) {
            if (!get(key + 'Editor').hidden) return;
            const group = groups[key], title = get(group.title).textContent;
            const titleDraft = get(key + 'TitleDraft'), bodyDraft = get(key + 'BodyDraft');
            titleDraft.value = key === 'source' ? get('titleDescBox').value :
                (title ? title.slice(3, -3) : '');
            bodyDraft.value = get(group.body).value;
            get(key + 'Display').hidden = true;
            get(key + 'Editor').hidden = false;
            get(key + 'Edit').setAttribute('aria-expanded', 'true');
            autoResize(titleDraft);
            autoResize(bodyDraft);
            titleDraft.focus();
        },
        save(key) {
            const group = groups[key], title = get(key + 'TitleDraft').value;
            get(group.title).textContent = title ? `...${title}...` : '';
            get(group.body).value = get(key + 'BodyDraft').value;
            if (key === 'source') get('titleDescBox').value = title;
            close(key, true);
            autoResize(get(group.body));
            if (key === 'response' && typeof responseEdited === 'function') responseEdited();
        },
        cancel(key) { close(key, true); },
        reset(key) { close(key, false); }
    };
})();
