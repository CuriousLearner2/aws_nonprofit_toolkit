/**
 * DonorTrust v1 — Phase 0 Interactions
 * Minimal vanilla JavaScript for prototype UI affordances
 */

// ============================================================================
// MODAL MANAGEMENT
// ============================================================================

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
    }
}

function notifyModalClose(modal) {
    if (modal && modal.id === 'record-modal' && typeof window.restoreRecordModalState === 'function') {
        window.restoreRecordModalState(modal);
    }
}

function finalizeModalClose(modal) {
    if (!modal) {
        return;
    }
    notifyModalClose(modal);
    if (modal.dataset) {
        modal.dataset.requestToken = '';
    }
    modal.classList.remove('show');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        finalizeModalClose(modal);
    }
}

// Close modal when clicking outside
document.addEventListener('click', function (event) {
    if (event.target.classList.contains('modal')) {
        finalizeModalClose(event.target);
    }
});

// ============================================================================
// TABLE SELECTION & REVIEW BUTTON
// ============================================================================

function updateReviewButtonState() {
    const checkboxes = document.querySelectorAll('input[type="checkbox"].row-selector');
    const reviewButton = document.getElementById('review-selected-btn');
    if (!reviewButton) return;

    const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;

    if (checkedCount === 0) {
        reviewButton.textContent = 'Review Selected (0)';
        reviewButton.disabled = true;
    } else {
        reviewButton.textContent = `Review Selected (${checkedCount})`;
        reviewButton.disabled = false;
    }
}

// Attach listeners to row checkboxes
document.addEventListener('DOMContentLoaded', function () {
    const checkboxes = document.querySelectorAll('input[type="checkbox"].row-selector');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateReviewButtonState);
    });

    // Set initial state
    updateReviewButtonState();

    // Duplicate reviewer notes requirement
    const duplicateForm = document.getElementById('duplicate-form');
    if (duplicateForm) {
        const samePersonButton = document.getElementById('mark-same-person-btn');
        const notesField = document.getElementById('reviewer-notes');

        if (samePersonButton && notesField) {
            const updateButtonState = () => {
                const hasConflict = document.querySelector('.conflicting-evidence-list li') !== null;
                const hasNotes = notesField.value.trim().length > 0;

                if (hasConflict && !hasNotes) {
                    samePersonButton.disabled = true;
                } else {
                    samePersonButton.disabled = false;
                }
            };

            notesField.addEventListener('input', updateButtonState);
            updateButtonState();
        }
    }

    // Action responses (confirm/reject/defer)
    document.querySelectorAll('[data-action]').forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();
            const action = this.getAttribute('data-action');
            const itemId = this.getAttribute('data-item-id');
            handleAction(action, itemId);
        });
    });
});

// ============================================================================
// ACTION RESPONSES (prototype-only; no persistence)
// ============================================================================

function handleAction(action, itemId) {
    let message = '';

    switch (action) {
        case 'confirm':
            message = `✓ Confirmed: #${itemId}`;
            break;
        case 'reject':
            message = `✗ Rejected: #${itemId}`;
            break;
        case 'different':
            message = `✗ Marked Different: #${itemId}`;
            break;
        case 'defer':
            message = `⏱ Deferred: #${itemId}`;
            break;
        case 'mark-same-person':
            message = `✓ Marked as Same Person: #${itemId}`;
            break;
        case 'confirm-normalization':
            message = `✓ Normalization Confirmed: #${itemId}`;
            break;
        case 'reject-normalization':
            message = `✗ Normalization Rejected: #${itemId}`;
            break;
        case 'defer-normalization':
            message = `⏱ Normalization Deferred: #${itemId}`;
            break;
        case 'confirm-household':
            message = `✓ Household Confirmed: #${itemId}`;
            break;
        case 'reject-household':
            message = `✗ Household Rejected: #${itemId}`;
            break;
        case 'defer-household':
            message = `⏱ Household Deferred: #${itemId}`;
            break;
        default:
            message = `Action: ${action}`;
    }

    showToast(message);
}

// ============================================================================
// TOAST NOTIFICATIONS
// ============================================================================

function showToast(message, duration = 3000) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: #10b981;
        color: white;
        padding: 12px 20px;
        border-radius: 4px;
        font-size: 14px;
        z-index: 2000;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ============================================================================
// HOUSEHOLD CONFIRMATION MODAL
// ============================================================================

function confirmHousehold(householdId) {
    const modal = document.getElementById('household-confirm-modal');
    if (modal) {
        modal.setAttribute('data-household-id', householdId);
        openModal('household-confirm-modal');
    }
}

function submitHouseholdConfirmation() {
    const modal = document.getElementById('household-confirm-modal');
    const householdId = modal.getAttribute('data-household-id');
    closeModal('household-confirm-modal');
    handleAction('confirm-household', householdId);
}

// ============================================================================
// EXPORT PACKAGE MODAL
// ============================================================================

function generateExportPackage() {
    const modal = document.getElementById('generate-export-modal');
    if (modal) {
        openModal('generate-export-modal');
    }
}

function submitExportGeneration() {
    closeModal('generate-export-modal');
    showToast('✓ Export package generated. Ready for download.');
}

// ============================================================================
// FILTER TOGGLE
// ============================================================================

function toggleFilter(filterId) {
    const filter = document.getElementById(filterId);
    if (filter) {
        filter.classList.toggle('expanded');
    }
}
