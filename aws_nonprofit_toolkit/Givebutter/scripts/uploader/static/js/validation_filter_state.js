(function (root, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.householderValidationFilterState = factory();
    }
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    const NO_ISSUES = 'No issues';
    const TOGGLEABLE = new Set(['Blocking', 'Warning']);

    function normalize(selection) {
        return Array.isArray(selection) ? selection.filter(Boolean) : [];
    }

    function transition(selection, action) {
        const current = new Set(normalize(selection));
        if (action === 'all') return [];
        if (action === NO_ISSUES) return [NO_ISSUES];
        if (TOGGLEABLE.has(action)) {
            current.delete(NO_ISSUES);
            if (current.has(action)) current.delete(action);
            else current.add(action);
        }
        return Array.from(current).filter(value => value === 'Blocking' || value === 'Warning');
    }

    function matches(rowStatus, selection) {
        const current = normalize(selection);
        if (current.length === 0) return true;
        if (current.includes(NO_ISSUES)) return rowStatus === NO_ISSUES;
        return current.includes(rowStatus);
    }

    return { transition, matches };
}));
