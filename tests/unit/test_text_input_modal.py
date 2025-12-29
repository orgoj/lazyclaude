"""Tests for TextInputModal widget."""

import pytest

from lazyclaude.widgets.text_input_modal import TextInputModal


class TestTextInputModal:
    """Tests for TextInputModal widget."""

    def test_initial_state_is_hidden(self) -> None:
        """Widget should be hidden by default."""
        modal = TextInputModal()
        assert not modal.is_visible

    def test_show_adds_visible_class(self) -> None:
        """show() should add visible class."""
        modal = TextInputModal()
        modal.show("Enter value...")
        assert modal.has_class("visible")
        assert modal.is_visible

    def test_hide_removes_visible_class(self) -> None:
        """hide() should remove visible class."""
        modal = TextInputModal()
        modal.add_class("visible")
        modal.hide()
        assert not modal.has_class("visible")
        assert not modal.is_visible

    def test_show_stores_context(self) -> None:
        """show() should store the context."""
        modal = TextInputModal()
        modal.show("Enter value...", context="test_context")
        assert modal._input_context == "test_context"

    def test_show_stores_placeholder(self) -> None:
        """show() should store the placeholder."""
        modal = TextInputModal()
        modal.show("Custom placeholder...")
        assert modal._placeholder == "Custom placeholder..."

    def test_default_placeholder(self) -> None:
        """Default placeholder should be 'Enter value...'."""
        modal = TextInputModal()
        assert modal._placeholder == "Enter value..."

    def test_default_context_is_none(self) -> None:
        """Default context should be None."""
        modal = TextInputModal()
        assert modal._input_context is None


class TestTextInputModalMessages:
    """Tests for TextInputModal message emission."""

    @pytest.mark.asyncio
    async def test_cancel_posts_input_cancelled(self) -> None:
        """action_cancel should post InputCancelled message."""
        modal = TextInputModal()
        modal._input_context = "test_context"

        messages: list[TextInputModal.InputCancelled] = []

        def capture_message(msg: TextInputModal.InputCancelled) -> None:
            messages.append(msg)

        modal.post_message = capture_message  # type: ignore
        modal.remove_class = lambda _: None  # type: ignore

        modal.action_cancel()

        assert len(messages) == 1
        assert isinstance(messages[0], TextInputModal.InputCancelled)
        assert messages[0].context == "test_context"

    @pytest.mark.asyncio
    async def test_cancel_hides_modal(self) -> None:
        """action_cancel should hide the modal."""
        modal = TextInputModal()
        modal.add_class("visible")

        modal.post_message = lambda _: None  # type: ignore

        modal.action_cancel()

        assert not modal.has_class("visible")


class TestTextInputModalBindings:
    """Tests for TextInputModal key bindings."""

    def test_has_escape_binding(self) -> None:
        """Should have binding for escape."""
        bindings = {b.key for b in TextInputModal.BINDINGS}
        assert "escape" in bindings


class TestInputSubmittedMessage:
    """Tests for InputSubmitted message."""

    def test_input_submitted_stores_value(self) -> None:
        """InputSubmitted should store the submitted value."""
        msg = TextInputModal.InputSubmitted("test value")
        assert msg.value == "test value"

    def test_input_submitted_stores_context(self) -> None:
        """InputSubmitted should store the context."""
        msg = TextInputModal.InputSubmitted("value", context="my_context")
        assert msg.context == "my_context"

    def test_input_submitted_context_defaults_to_none(self) -> None:
        """InputSubmitted context should default to None."""
        msg = TextInputModal.InputSubmitted("value")
        assert msg.context is None


class TestInputCancelledMessage:
    """Tests for InputCancelled message."""

    def test_input_cancelled_stores_context(self) -> None:
        """InputCancelled should store the context."""
        msg = TextInputModal.InputCancelled(context="my_context")
        assert msg.context == "my_context"

    def test_input_cancelled_context_defaults_to_none(self) -> None:
        """InputCancelled context should default to None."""
        msg = TextInputModal.InputCancelled()
        assert msg.context is None
