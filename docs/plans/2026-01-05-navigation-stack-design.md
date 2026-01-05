# Navigation Stack Design

## Overview

Implement navigation stack for Normal view to support viewing customizations from different sources (all, plugin preview) with back navigation via Esc.

## Architecture

### Data Structure

Navigation stack stored in `App`:

```python
_nav_stack: list[tuple[list[Customization], ViewMode | None]]
```

- **data**: `list[Customization]` - customizations to display
- **prev_view**: `ViewMode | None` - previous view mode to return to on Esc

### Stack Layers

**Base layer** (always present):
```python
[(all_customizations, None)]
```

**Plugin preview layer**:
```python
[(all_customizations, None), (plugin_customizations, ViewMode.MARKETPLACE)]
```

## Implementation

### App Methods

```python
class App(App):
    def __init__(self):
        self._nav_stack: list[tuple[list[Customization], ViewMode | None]] = []
        self._initialize_nav_stack()

    def _initialize_nav_stack(self) -> None:
        """Initialize navigation stack with base layer."""
        base_data = self._discovery.discover_all()
        self._nav_stack = [(base_data, None)]

    def _get_current_data(self) -> list[Customization]:
        """Get current data from top of stack."""
        return self._nav_stack[-1][0]

    def _push_nav_state(self, data: list[Customization], prev_mode: ViewMode) -> None:
        """Push new navigation state and switch to Normal view."""
        self._nav_stack.append((data, prev_mode))
        self._switch_view_mode(ViewMode.NORMAL)
        self._refresh_normal_view()

    def _navigate_back(self) -> None:
        """Navigate back in history."""
        if not self._nav_stack:
            logger.error("Navigation stack is empty!")
            return

        current_data, prev_mode = self._nav_stack[-1]

        if prev_mode is not None:
            self._nav_stack.pop()
            self._switch_view_mode(prev_mode)

    def _refresh_normal_view(self) -> None:
        """Refresh Normal view with current data."""
        current_data = self._get_current_data()
        for panel in self._type_panels:
            panel.update_data(current_data)
        self._combined_panel.update_data(current_data)
```

### Key Bindings

- **Esc**: Calls `_navigate_back()`
- **"p" in Marketplace**: Calls `_push_nav_state(plugin_data, ViewMode.MARKETPLACE)`

## User Flow

1. **Start**: Normal view displays all customizations (base layer)
2. **Marketplace → "p"**: Push plugin data, switch to Normal view
3. **Esc**: Pop stack, return to previous view (Marketplace)
4. **Multiple plugins**: Stack grows, Esc navigates back through history

## Error Handling

- **Plugin discovery fails**: Return empty list `[]`, display empty Normal view
- **Stack empty**: Log error, return early (should never happen with base layer)
- **Invalid data type**: Log error, use empty list

## Testing

### Test Scenarios

1. **Base layer**: App start displays all customizations, Esc does nothing
2. **Plugin preview**: Marketplace → "p" → plugin customizations → Esc → back to Marketplace
3. **Multiple history**: Marketplace → A → B → Esc → A → Esc → Marketplace
4. **Refresh**: Normal view → "r" → reload current data
5. **Edge cases**: Empty plugin, discovery failure

### Unit Test Example

```python
def test_nav_stack():
    # Base layer
    assert len(app._nav_stack) == 1
    assert app._nav_stack[-1][1] is None

    # Push plugin preview
    app._push_nav_state(plugin_data, ViewMode.MARKETPLACE)
    assert len(app._nav_stack) == 2
    assert app._get_current_data() == plugin_data

    # Navigate back
    app._navigate_back()
    assert len(app._nav_stack) == 1
```

## Future Extensions

This design supports:
- Multiple view modes (each with own stack if needed)
- Different customization sources (remote API, files, etc.)
- Complex navigation histories
- Browser-like back/forward (if needed)
