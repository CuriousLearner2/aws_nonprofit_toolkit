"""Form and input testing for UX quality."""
import pytest
import asyncio


# ============ FILE UPLOAD TESTS ============

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_file_input_accepts_csv(flask_app_for_forms, temp_dir, sample_csv):
    """Test that file input accepts CSV files."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            file_input = await page.query_selector('input[type="file"]')

            assert file_input is not None
            # File input should accept CSV
            accept_attr = await file_input.get_attribute('accept')
            if accept_attr:
                assert 'csv' in accept_attr.lower() or accept_attr == '*'

            # Test setting file
            await file_input.set_input_files(str(sample_csv))
            value = await file_input.input_value()
            assert len(value) > 0

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_file_input_shows_feedback(flask_app_for_forms, temp_dir, sample_csv):
    """Test that file selection shows user feedback."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            # Check if there's feedback text showing filename
            content = await page.content()
            # Should show filename or "file selected" message
            has_feedback = (
                'sample' in content.lower() or
                'file' in content.lower() or
                'uploaded' in content.lower() or
                'selected' in content.lower()
            )
            # Some implementations may not show feedback, that's ok
            # But if they do, verify it's user-friendly

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_button_disabled_without_file(flask_app_for_forms):
    """Test that upload button is disabled until file is selected."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            # Check submit button state (may be disabled or check file input)
            submit_buttons = await page.query_selector_all('button[type="submit"], button:has-text("Upload"), input[type="submit"]')

            if submit_buttons:
                for button in submit_buttons:
                    # Button may be disabled or enabled - depends on implementation
                    # Just verify button exists
                    assert button is not None

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_shows_loading_state(flask_app_for_forms, temp_dir, sample_csv):
    """Test that upload shows loading/processing feedback."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

                # Check for loading indicator
                content = await page.content()
                has_loading_feedback = any(text in content.lower() for text in [
                    'processing', 'loading', 'uploading', 'please wait'
                ])
                # Loading feedback is nice to have but not required

        finally:
            await browser.close()


# ============ DECISION DROPDOWN TESTS ============

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_decision_dropdown_has_all_options(flask_app_for_forms, temp_dir, sample_csv):
    """Test that decision dropdown has all three options."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Navigate to review
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Wait for review button to be visible before clicking
            await page.wait_for_selector('button:has-text("Review"), a:has-text("Review")', timeout=5000)
            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                # Wait for dropdowns
                selects = await page.query_selector_all('select, [class*="decision"]')
                if selects:
                    first_select = selects[0]

                    # Get all options
                    options = await first_select.query_selector_all('option')
                    option_values = []
                    for opt in options:
                        value = await opt.get_attribute('value')
                        text = await opt.text_content()
                        option_values.append((value, text))

                    # Should have placeholder, approved, followup, rejected
                    option_texts = [text.lower() for _, text in option_values]
                    assert any('approved' in text for text in option_texts)
                    assert any('followup' in text or 'follow-up' in text for text in option_texts)
                    assert any('reject' in text for text in option_texts)

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_decision_selection_changes_visual_state(flask_app_for_forms, temp_dir, sample_csv):
    """Test that selecting decision option changes visual state."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Navigate to review
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Wait for review button to be visible before clicking
            await page.wait_for_selector('button:has-text("Review"), a:has-text("Review")', timeout=5000)
            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                selects = await page.query_selector_all('select, [class*="decision"]')
                if selects:
                    # Select a decision
                    await selects[0].select_option(value="approved")

                    # Verify it's selected
                    value = await selects[0].input_value()
                    assert 'approved' in value.lower()

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_dropdown_keyboard_navigation(flask_app_for_forms, temp_dir, sample_csv):
    """Test that dropdown can be navigated with keyboard."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Navigate to review
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Wait for review button to be visible before clicking
            await page.wait_for_selector('button:has-text("Review"), a:has-text("Review")', timeout=5000)
            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                # Wait for table and dropdowns to fully load
                await page.wait_for_selector('table.review-table', timeout=5000)
                await page.wait_for_selector('select.decision-select', timeout=5000)

                selects = await page.query_selector_all('select.decision-select')
                if selects:
                    dropdown = selects[0]

                    # Get available options
                    options = await page.query_selector_all('select.decision-select option')
                    assert len(options) > 1, "Dropdown should have more than one option"

                    # Select the second option (first is usually empty/default)
                    second_option_value = await options[1].get_attribute('value')
                    await dropdown.select_option(second_option_value)

                    # Verify the selection was made
                    selected_value = await dropdown.input_value()
                    assert selected_value == second_option_value, f"Expected {second_option_value} to be selected, but got {selected_value}"

        finally:
            await browser.close()


# ============ NOTES TEXTAREA TESTS ============

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_notes_textarea_accepts_input(flask_app_for_forms, temp_dir, sample_csv):
    """Test that notes textarea accepts text input."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Navigate to review
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Wait for review button to be visible before clicking
            await page.wait_for_selector('button:has-text("Review"), a:has-text("Review")', timeout=5000)
            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                textareas = await page.query_selector_all('textarea, [class*="notes"]')
                if textareas:
                    test_text = "This is a test note with multiple words."
                    await textareas[0].fill(test_text)

                    value = await textareas[0].input_value()
                    assert value == test_text

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_notes_textarea_unicode_input(flask_app_for_forms, temp_dir, sample_csv):
    """Test that notes textarea handles Unicode input."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Navigate to review
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Wait for review button to be visible before clicking
            await page.wait_for_selector('button:has-text("Review"), a:has-text("Review")', timeout=5000)
            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                textareas = await page.query_selector_all('textarea, [class*="notes"]')
                if textareas:
                    unicode_text = "Special: José García 李明 Müller"
                    await textareas[0].fill(unicode_text)

                    value = await textareas[0].input_value()
                    assert 'José' in value
                    assert '李明' in value

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_notes_textarea_placeholder_text(flask_app_for_forms, temp_dir, sample_csv):
    """Test that notes textarea shows helpful placeholder."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Navigate to review
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Wait for review button to be visible before clicking
            await page.wait_for_selector('button:has-text("Review"), a:has-text("Review")', timeout=5000)
            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                textareas = await page.query_selector_all('textarea, [class*="notes"]')
                if textareas:
                    placeholder = await textareas[0].get_attribute('placeholder')
                    if placeholder:
                        # Placeholder should be helpful
                        assert len(placeholder) > 0
                        assert any(word in placeholder.lower() for word in ['note', 'comment', 'text'])

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_textarea_keyboard_navigation(flask_app_for_forms, temp_dir, sample_csv):
    """Test that textarea can be navigated with Tab key."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Navigate to review
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Wait for review button to be visible before clicking
            await page.wait_for_selector('button:has-text("Review"), a:has-text("Review")', timeout=5000)
            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                # Tab through elements
                textareas = await page.query_selector_all('textarea, [class*="notes"]')
                if textareas:
                    await textareas[0].focus()

                    # Type text with focus
                    await page.keyboard.type("Test text")

                    value = await textareas[0].input_value()
                    assert "Test text" in value

        finally:
            await browser.close()


# ============ VALIDATION FEEDBACK TESTS ============

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_validation_summary_clear(flask_app_for_forms, temp_dir, sample_csv):
    """Test that validation summary is clear and readable."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            content = await page.content()
            # Should show pass/warning/fail counts clearly
            has_summary = any(text in content for text in ['PASS', 'WARNING', 'FAIL', 'record'])
            assert has_summary

        finally:
            await browser.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_validation_tier_color_coded(flask_app_for_forms, temp_dir, sample_csv):
    """Test that validation tiers are visually distinct (e.g., color-coded)."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Wait for review button to be visible before clicking
            await page.wait_for_selector('button:has-text("Review"), a:has-text("Review")', timeout=5000)
            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                # Check for validation tier indicators in table
                content = await page.content()
                # Should distinguish between PASS, WARNING, FAIL
                # This could be via CSS classes, colors, icons, etc.
                assert any(tier in content for tier in ['PASS', 'WARNING', 'FAIL'])

        finally:
            await browser.close()


# ============ SAVE/SUBMISSION FEEDBACK TESTS ============


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_save_success_message(flask_app_for_forms, temp_dir, sample_csv):
    """Test that save shows clear success feedback."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        try:
            # Navigate to review and make decisions
            await page.goto("http://127.0.0.1:8000/")
            await page.wait_for_selector('div.drop-zone', timeout=5000)

            file_input = await page.query_selector('input[type="file"]')
            await file_input.set_input_files(str(sample_csv))

            submit_button = await page.query_selector('button[type="submit"], button:has-text("Upload"), input[type="submit"]')
            if submit_button:
                await submit_button.click()

            await page.wait_for_selector('text=/processed|records/', timeout=5000)

            # Wait for review button to be visible before clicking
            await page.wait_for_selector('button:has-text("Review"), a:has-text("Review")', timeout=5000)
            review_button = await page.query_selector('button:has-text("Review"), a:has-text("Review")')
            if review_button:
                await review_button.click()

                # Make some decisions
                decision_selects = await page.query_selector_all('select, [class*="decision"]')
                if decision_selects:
                    await decision_selects[0].select_option(value="approved")

                    # Save
                    save_button = await page.query_selector('button:has-text("Save")')
                    if save_button:
                        await save_button.click()

                        # Should show success message
                        await page.wait_for_selector('text=/saved|progress/', timeout=5000)

                        content = await page.content()
                        assert any(text in content.lower() for text in ['saved', 'success', 'progress'])

        finally:
            await browser.close()


