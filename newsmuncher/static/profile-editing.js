/* Page-local drafts: no persistence or generation requests from Edit/Save/Cancel. */
const profileEditing = (() => {
    const fields = {
        sourceTitle: {id: 'sourceTitleHeading', title: true, source: true},
        sourceBody: {id: 'nonsenseBox'},
        responseTitle: {id: 'crazyTitleBox', title: true},
        responseBody: {id: 'crazyExtractBox'}
    };
    const get = id => document.getElementById(id);
    function close(key, focus) {
        const field = fields[key];
        get(field.id).hidden = false;
        get(key + 'Editor').hidden = true;
        get(key + 'Edit').setAttribute('aria-expanded', 'false');
        if (focus) get(key + 'Edit').focus();
    }
    return {
        edit(key) {
            const field = fields[key], display = get(field.id), draft = get(key + 'Draft');
            draft.value = field.source ? get('titleDescBox').value :
                field.title ? (display.textContent ? display.textContent.slice(3, -3) : '') : display.value;
            display.hidden = true;
            get(key + 'Editor').hidden = false;
            get(key + 'Edit').setAttribute('aria-expanded', 'true');
            draft.focus();
            if (!field.title) autoResize(draft);
        },
        save(key) {
            const field = fields[key], value = get(key + 'Draft').value, display = get(field.id);
            if (field.title) display.textContent = value ? `...${value}...` : '';
            else display.value = value;
            if (field.source) get('titleDescBox').value = value;
            close(key, true);
            if (key.startsWith('response') && typeof responseEdited === 'function') responseEdited();
            if (!field.title) autoResize(display);
        },
        cancel(key) { close(key, true); },
        reset(group) {
            Object.keys(fields).filter(key => key.startsWith(group)).forEach(key => close(key, false));
        }
    };
})();
