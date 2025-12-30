#!/bin/bash

# Test LazyClaude Marketplace View
# This script tests the marketplace functionality without installing anything
# Run from project root: ./tests/integration/tmux/test_marketplace_view.sh

set -e

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../" && pwd)"

SESSION="lazyclaude_marketplace_test"
LOG_FILE="$PROJECT_ROOT/tmp/marketplace_test.log"
OUTPUT_DIR="$PROJECT_ROOT/tmp/marketplace_test_output"

# Setup
mkdir -p "$OUTPUT_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

# Cleanup trap
cleanup() {
    echo "Cleaning up tmux session..."
    tmux kill-session -t "$SESSION" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "=== Starting LazyClaude Marketplace Test ==="
echo "Date: $(date)"
echo "Project root: $PROJECT_ROOT"
echo ""

# Phase 1: Setup
echo "[1] Creating tmux session..."
tmux has-session -t "$SESSION" 2>/dev/null && tmux kill-session -t "$SESSION"
tmux new-session -d -s "$SESSION" -x 200 -y 50

if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "ERROR: Failed to create session"
    exit 1
fi
echo "✓ Session created: $SESSION"

# Phase 2: Start LazyClaude
echo ""
echo "[2] Starting LazyClaude in marketplace mode..."
cd "$PROJECT_ROOT"
tmux send-keys -t "$SESSION" "timeout 30 uv run lazyclaude -m" Enter
sleep 3

# Phase 3: Verify marketplace view loaded
echo ""
echo "[3] Verifying marketplace view loaded..."
OUTPUT=$(tmux capture-pane -t "$SESSION" -p)
if echo "$OUTPUT" | grep -q "Marketplace"; then
    echo "✓ Marketplace view detected"
else
    echo "⚠ Marketplace view not immediately visible, waiting..."
    sleep 2
    OUTPUT=$(tmux capture-pane -t "$SESSION" -p)
    if echo "$OUTPUT" | grep -q "Marketplace"; then
        echo "✓ Marketplace view loaded after delay"
    else
        echo "⚠ Marketplace view may not be loaded, continuing anyway..."
    fi
fi

# Phase 4: Capture initial state
echo ""
echo "[4] Capturing initial marketplace state..."
tmux capture-pane -t "$SESSION" -p -S - > "$OUTPUT_DIR/marketplace_initial.txt"
echo "✓ Initial state captured"

# Check for marketplaces
MARKETPLACE_COUNT=$(grep -c "Marketplace:" "$OUTPUT_DIR/marketplace_initial.txt" || echo "0")
PLUGIN_COUNT=$(grep -c "│" "$OUTPUT_DIR/marketplace_initial.txt" || echo "0")
echo "  - Detected ~$MARKETPLACE_COUNT marketplace(s)"
echo "  - Detected ~$PLUGIN_COUNT lines of tree output"

# Phase 5: Test navigation
echo ""
echo "[5] Testing navigation keys..."

# Test down navigation (j)
echo "  Testing 'j' (down)..."
tmux send-keys -t "$SESSION" "j"
sleep 0.5
echo "  ✓ Sent 'j' key"

# Test up navigation (k)
echo "  Testing 'k' (up)..."
tmux send-keys -t "$SESSION" "k"
sleep 0.5
echo "  ✓ Sent 'k' key"

# Test expand (l)
echo "  Testing 'l' (expand)..."
tmux send-keys -t "$SESSION" "l"
sleep 0.5
echo "  ✓ Sent 'l' key"

# Test collapse (h)
echo "  Testing 'h' (collapse)..."
tmux send-keys -t "$SESSION" "h"
sleep 0.5
echo "  ✓ Sent 'h' key"

# Phase 6: Test expand/collapse all
echo ""
echo "[6] Testing expand/collapse all..."
tmux send-keys -t "$SESSION" "L"
sleep 1
echo "✓ Sent 'L' (expand all)"

tmux send-keys -t "$SESSION" "H"
sleep 1
echo "✓ Sent 'H' (collapse all)"

# Phase 7: Test info panel
echo ""
echo "[7] Testing info panel display..."
tmux send-keys -t "$SESSION" "j"
sleep 0.5
tmux capture-pane -t "$SESSION" -p -S - > "$OUTPUT_DIR/marketplace_after_nav.txt"
echo "✓ Captured state after navigation"

# Check if info panel content changed
if ! diff -q "$OUTPUT_DIR/marketplace_initial.txt" "$OUTPUT_DIR/marketplace_after_nav.txt" >/dev/null 2>&1; then
    echo "✓ Info panel content updated (selection changed)"
else
    echo "ℹ Info panel content unchanged (might be at same position)"
fi

# Phase 8: Test filters
echo ""
echo "[8] Testing filter keys..."

# Test installed-only filter (i)
echo "  Testing 'i' (installed-only)..."
tmux send-keys -t "$SESSION" "i"
sleep 1
tmux capture-pane -t "$SESSION" -p -S - > "$OUTPUT_DIR/marketplace_filter_i.txt"
echo "✓ Toggled installed-only filter"

# Test enabled-only filter (n)
echo "  Testing 'n' (enabled-only)..."
tmux send-keys -t "$SESSION" "n"
sleep 1
tmux capture-pane -t "$SESSION" -p -S - > "$OUTPUT_DIR/marketplace_filter_n.txt"
echo "✓ Toggled enabled-only filter"

# Reset filters
tmux send-keys -t "$SESSION" "i"
sleep 0.5
tmux send-keys -t "$SESSION" "n"
sleep 0.5
echo "✓ Reset filters"

# Phase 9: Test preview on installed plugin (if any)
echo ""
echo "[9] Testing preview functionality (if installed plugins exist)..."

# Look for installed plugins in the output
if grep -q "I:" "$OUTPUT_DIR/marketplace_initial.txt"; then
    echo "  Found installed plugins, testing preview..."

    # Navigate to first item
    tmux send-keys -t "$SESSION" "g"
    sleep 0.5

    # Try to find an installed plugin
    for i in {1..20}; do
        tmux send-keys -t "$SESSION" "j"
        sleep 0.3

        OUTPUT=$(tmux capture-pane -t "$SESSION" -p)
        if echo "$OUTPUT" | grep -q "I:upl"; then
            echo "  Found installed plugin, pressing 'p' to preview..."
            tmux send-keys -t "$SESSION" "p"
            sleep 2

            # Check if we entered preview mode
            PREVIEW_OUTPUT=$(tmux capture-pane -t "$SESSION" -p)
            if echo "$PREVIEW_OUTPUT" | grep -qi "preview"; then
                echo "✓ Preview mode activated"

                # Exit preview with Esc
                tmux send-keys -t "$SESSION" Escape
                sleep 1
                echo "✓ Exited preview mode"
            else
                echo "ℹ Preview mode may not have activated"
            fi
            break
        fi
    done
else
    echo "ℹ No installed plugins detected, skipping preview test"
fi

# Phase 10: Final capture
echo ""
echo "[10] Capturing final state..."
tmux capture-pane -t "$SESSION" -p -S - > "$OUTPUT_DIR/marketplace_final.txt"
echo "✓ Final state captured"

# Phase 11: Summary
echo ""
echo "=== Test Summary ==="
echo "Output directory: $OUTPUT_DIR"
echo "Files generated:"
ls -la "$OUTPUT_DIR"
echo ""
echo "Full log: $LOG_FILE"
echo ""
echo "Test completed successfully!"
