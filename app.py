import streamlit as st
import requests

# OpenRouter API URL
OPENROUTER_API_URL = "https://openrouter.ai/api/frontend/models"

# Fetch pricing data from OpenRouter API


def fetch_pricing_data():
    try:
        response = requests.get(OPENROUTER_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        pricing_data = {}
        available_models = []

        # Check if we got models
        models = data.get("data", [])
        if not models:
            st.error("No models returned from OpenRouter API")
            return use_fallback_pricing()

        for model in models:
            slug = model.get("slug", "unknown")
            endpoint = model.get("endpoint", {})

            if endpoint:
                pricing = endpoint.get("pricing", {})

                # Check if pricing has meaningful data (strings that can be converted to floats)
                prompt_price = pricing.get("prompt", "0")
                completion_price = pricing.get("completion", "0")

                try:
                    prompt_float = float(prompt_price) if prompt_price else 0.0
                    completion_float = float(
                        completion_price) if completion_price else 0.0

                    # Include models even with 0 pricing (free models)
                    pricing_data[slug] = {
                        "prompt": prompt_float,  # Already in per-token format
                        "completion": completion_float
                    }
                    available_models.append(slug)

                except (ValueError, TypeError):
                    # Skip models with invalid pricing data
                    continue

        # If no models found, use fallback
        if not available_models:
            st.warning(
                "OpenRouter API returned no valid pricing data. Using fallback pricing estimates.")
            return use_fallback_pricing()

        st.success(
            f"Successfully loaded {len(available_models)} models from OpenRouter API")
        return pricing_data, available_models

    except requests.RequestException as e:
        st.error(f"Failed to fetch pricing data: {e}")
        st.info("Using fallback pricing estimates.")
        return use_fallback_pricing()

# Fallback pricing data when API fails or returns no pricing


def use_fallback_pricing():
    fallback_pricing = {
        # Free model
        "google/gemma-2-9b": {"prompt": 0.000000, "completion": 0.000000},
        # Estimated
        "qwen/qwen3-coder-flash": {"prompt": 0.00000045, "completion": 0.00000045},
        # Standard GPT-4 pricing
        "openai/gpt-4": {"prompt": 0.00003, "completion": 0.00006},
        "openai/gpt-3.5-turbo": {"prompt": 0.0000005, "completion": 0.0000015},
        "anthropic/claude-3-sonnet": {"prompt": 0.000003, "completion": 0.000015},
        "meta-llama/llama-3.1-8b": {"prompt": 0.0000002, "completion": 0.0000002}
    }
    available_models = list(fallback_pricing.keys())
    return fallback_pricing, available_models


# Default usage patterns per agent (monthly per teacher)
AGENT_USAGE_PATTERNS = {
    "Curriculum Mapping Agent": {
        "default_uses_per_month": 1,
        "tokens_per_use": 1000,
        "default_model": "google/gemma-3-12b-it",
        "description": "Monthly curriculum analysis"
    },
    "Content Sourcing Agent": {
        "default_uses_per_month": 1,
        "tokens_per_use": 5000,
        "default_model": "google/gemma-3-12b-it",
        "description": "Finding lesson resources"
    },
    "Planner Agent": {
        "default_uses_per_month": 4,
        "tokens_per_use": 4000,
        "default_model": "qwen/qwen3-8b",
        "description": "Bi-weekly lesson planning"
    },
    "Lesson Designer": {
        "default_uses_per_month": 4,
        "tokens_per_use": 5000,
        "default_model": "qwen/qwen3-8b",
        "description": "Creating lesson activities"
    },
    "Assessment Agent": {
        "default_uses_per_month": 4,
        "tokens_per_use": 5000,
        "default_model": "qwen/qwen3-8b",
        "description": "Generating assessments"
    },
    "Feedback Agent": {
        "default_uses_per_month": 4,
        "tokens_per_use": 1000,
        "default_model": "google/gemma-3-12b-it",
        "description": "Student feedback review"
    },
    "Slide Generation Agent": {
        "default_uses_per_month": 4,
        "tokens_per_use": 4000,
        "default_model": "openai/gpt-4.1",
        "description": "Creating presentation slides"
    }
}

# Streamlit app
st.title("AIME Pricing Calculator")

# Fetch pricing data
pricing_data, available_models = fetch_pricing_data()

# Continue even if we're using fallback data

# Input: Number of teachers
num_teachers = st.number_input(
    "Number of Teachers", min_value=1, value=1, step=1)

# Agent configuration
st.header("Agent Configuration")
agent_configs = {}
for agent, config in AGENT_USAGE_PATTERNS.items():
    default_model_idx = available_models.index(
        config["default_model"]) if config["default_model"] in available_models else 0
    
    st.subheader(agent)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        model = st.selectbox(
            f"Model", available_models, index=default_model_idx, key=f"model_{agent}")
    
    with col2:
        uses_per_month = st.number_input(
            f"Uses per month", min_value=1, value=config["default_uses_per_month"], step=1, key=f"uses_{agent}")
    
    with col3:
        tokens_per_use = st.number_input(
            f"Tokens per use", min_value=10, value=config["tokens_per_use"], step=10, key=f"tokens_{agent}")
    
    st.caption(f"💡 {config['description']} • Total monthly tokens: {uses_per_month * tokens_per_use:,}")
    
    agent_configs[agent] = {
        "model": model, 
        "uses_per_month": uses_per_month,
        "tokens_per_use": tokens_per_use,
        "total_tokens": uses_per_month * tokens_per_use
    }

# Calculate pricing
total_cost_per_teacher = 0
st.header("Pricing Breakdown")
for agent, config in agent_configs.items():
    model = config["model"]
    total_tokens = config["total_tokens"]
    uses_per_month = config["uses_per_month"]
    tokens_per_use = config["tokens_per_use"]
    
    prompt_tokens = total_tokens * 0.7  # 70% prompt
    completion_tokens = total_tokens * 0.3  # 30% completion
    prompt_cost = (prompt_tokens * pricing_data[model]["prompt"])
    completion_cost = (completion_tokens * pricing_data[model]["completion"])
    total_cost = prompt_cost + completion_cost
    total_cost_per_teacher += total_cost
    
    st.write(f"**{agent}**: ${total_cost:.6f}/month")
    st.write(f"   📊 {uses_per_month} uses × {tokens_per_use} tokens = {total_tokens:,} tokens")
    st.write(f"   💰 Prompt: {prompt_tokens:.0f} tokens @ ${prompt_cost:.6f} | Completion: {completion_tokens:.0f} tokens @ ${completion_cost:.6f}")
    st.write("---")

# Total cost
total_cost_all_teachers = total_cost_per_teacher * num_teachers
st.header("Total Cost")
st.write(f"Cost per Teacher: ${total_cost_per_teacher:.6f}")
st.write(
    f"Total Cost for {num_teachers} Teachers: ${total_cost_all_teachers:.2f}")

# Notes
st.markdown("""
### Notes
- Pricing is fetched in real-time from https://openrouter.ai/api/frontend/models.
- Configure each agent by selecting model, monthly usage frequency, and tokens per use.
- Total tokens = Uses per month × Tokens per use.
- Assumes 70% prompt and 30% completion tokens per interaction.
- Free models show $0 pricing; costs reflect current OpenRouter rates.
- Actual costs may vary with API updates, usage patterns, or model availability.
""")
