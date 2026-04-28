#!/bin/bash
# Run LLM route integration tests on both GPT-4o and Claude Sonnet 4.6
# Usage: bash run_route_llm_tests.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

REPORT_DIR="tests/eval/reports"
mkdir -p "$REPORT_DIR"

ENV_BAK=".env.bak"
cp .env "$ENV_BAK"

run_tests() {
    local provider=$1
    local model=$2
    local report_suffix=$3

    echo "========================================"
    echo " Running on $model"
    echo "========================================"

    # Patch .env for this run
    sed -i '' "s/^LLM_PROVIDER=.*/LLM_PROVIDER=$provider/" .env
    if [ "$provider" = "openai" ]; then
        sed -i '' "s/^OPENAI_MODEL=.*/OPENAI_MODEL=$model/" .env
    else
        sed -i '' "s/^ANTHROPIC_MODEL=.*/ANTHROPIC_MODEL=$model/" .env
    fi

    # Run with clean env (no inherited LLM_PROVIDER from shell)
    env -i HOME="$HOME" PATH="$PATH" \
        PYTHONPATH=backend \
        .venv/bin/pytest tests/eval/test_routes_llm.py -v -s --tb=short --timeout=120 \
        2>&1 | tee "$REPORT_DIR/route_llm_${report_suffix}.log" || true

    if [ -f "$REPORT_DIR/route_llm_results.json" ]; then
        cp "$REPORT_DIR/route_llm_results.json" "$REPORT_DIR/route_llm_results_${report_suffix}.json"
    fi

    cp "$ENV_BAK" .env
    echo ""
}

run_tests "openai" "gpt-4o" "gpt4o"
run_tests "anthropic" "claude-sonnet-4-6" "claude"

rm -f "$ENV_BAK"

echo "========================================"
echo " DONE — results saved to $REPORT_DIR"
echo "   GPT-4o:  route_llm_results_gpt4o.json"
echo "   Claude:  route_llm_results_claude.json"
echo "========================================"
