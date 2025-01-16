import os

import pytest

from tests.helpers.endpoints_helper import (
    check_agent_archival_memory_insert,
    check_agent_archival_memory_retrieval,
    check_agent_edit_core_memory,
    check_agent_recall_chat_memory,
    check_agent_uses_external_tool,
    check_first_response_is_valid_for_llm_endpoint,
    run_embedding_endpoint,
)
from tests.helpers.utils import retry_until_success, retry_until_threshold

# directories
embedding_config_dir = "tests/configs/embedding_model_configs"
llm_config_dir = "tests/configs/llm_model_configs"


# ======================================================================================================================
# OPENAI TESTS
# ======================================================================================================================
@pytest.mark.openai_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_openai_gpt_4o_returns_valid_first_message():
    filename = os.path.join(llm_config_dir, "openai-gpt-4o.json")
    response = check_first_response_is_valid_for_llm_endpoint(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.openai_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_openai_gpt_4o_uses_external_tool(mock_e2b_api_key_none):
    filename = os.path.join(llm_config_dir, "openai-gpt-4o.json")
    response = check_agent_uses_external_tool(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.openai_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_openai_gpt_4o_recall_chat_memory():
    filename = os.path.join(llm_config_dir, "openai-gpt-4o.json")
    response = check_agent_recall_chat_memory(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.openai_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_openai_gpt_4o_archival_memory_retrieval():
    filename = os.path.join(llm_config_dir, "openai-gpt-4o.json")
    response = check_agent_archival_memory_retrieval(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.openai_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_openai_gpt_4o_archival_memory_insert():
    filename = os.path.join(llm_config_dir, "openai-gpt-4o.json")
    response = check_agent_archival_memory_insert(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.openai_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_openai_gpt_4o_edit_core_memory():
    filename = os.path.join(llm_config_dir, "openai-gpt-4o.json")
    response = check_agent_edit_core_memory(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.openai_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_embedding_endpoint_openai():
    filename = os.path.join(embedding_config_dir, "openai_embed.json")
    run_embedding_endpoint(filename)


# ======================================================================================================================
# AZURE TESTS
# ======================================================================================================================
@pytest.mark.azure_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_azure_gpt_4o_mini_returns_valid_first_message():
    filename = os.path.join(llm_config_dir, "azure-gpt-4o-mini.json")
    response = check_first_response_is_valid_for_llm_endpoint(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.azure_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_azure_gpt_4o_mini_uses_external_tool(mock_e2b_api_key_none):
    filename = os.path.join(llm_config_dir, "azure-gpt-4o-mini.json")
    response = check_agent_uses_external_tool(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.azure_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_azure_gpt_4o_mini_recall_chat_memory():
    filename = os.path.join(llm_config_dir, "azure-gpt-4o-mini.json")
    response = check_agent_recall_chat_memory(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.azure_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_azure_gpt_4o_mini_archival_memory_retrieval():
    filename = os.path.join(llm_config_dir, "azure-gpt-4o-mini.json")
    response = check_agent_archival_memory_retrieval(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.azure_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_azure_gpt_4o_mini_edit_core_memory():
    filename = os.path.join(llm_config_dir, "azure-gpt-4o-mini.json")
    response = check_agent_edit_core_memory(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.azure_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_azure_embedding_endpoint():
    filename = os.path.join(embedding_config_dir, "azure_embed.json")
    run_embedding_endpoint(filename)


# ======================================================================================================================
# LETTA HOSTED
# ======================================================================================================================
def test_llm_endpoint_letta_hosted():
    filename = os.path.join(llm_config_dir, "letta-hosted.json")
    check_first_response_is_valid_for_llm_endpoint(filename)


def test_embedding_endpoint_letta_hosted():
    filename = os.path.join(embedding_config_dir, "letta-hosted.json")
    run_embedding_endpoint(filename)


# ======================================================================================================================
# LOCAL MODELS
# ======================================================================================================================
def test_embedding_endpoint_local():
    filename = os.path.join(embedding_config_dir, "local.json")
    run_embedding_endpoint(filename)


def test_llm_endpoint_ollama():
    filename = os.path.join(llm_config_dir, "ollama.json")
    check_first_response_is_valid_for_llm_endpoint(filename)


def test_embedding_endpoint_ollama():
    filename = os.path.join(embedding_config_dir, "ollama.json")
    run_embedding_endpoint(filename)


# ======================================================================================================================
# ANTHROPIC TESTS
# ======================================================================================================================
@pytest.mark.anthropic_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_claude_haiku_3_5_returns_valid_first_message():
    filename = os.path.join(llm_config_dir, "claude-3-5-haiku.json")
    response = check_first_response_is_valid_for_llm_endpoint(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.anthropic_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_claude_haiku_3_5_uses_external_tool(mock_e2b_api_key_none):
    filename = os.path.join(llm_config_dir, "claude-3-5-haiku.json")
    response = check_agent_uses_external_tool(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.anthropic_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_claude_haiku_3_5_recall_chat_memory():
    filename = os.path.join(llm_config_dir, "claude-3-5-haiku.json")
    response = check_agent_recall_chat_memory(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.anthropic_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_claude_haiku_3_5_archival_memory_retrieval():
    filename = os.path.join(llm_config_dir, "claude-3-5-haiku.json")
    response = check_agent_archival_memory_retrieval(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.anthropic_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_claude_haiku_3_5_edit_core_memory():
    filename = os.path.join(llm_config_dir, "claude-3-5-haiku.json")
    response = check_agent_edit_core_memory(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


# ======================================================================================================================
# GROQ TESTS
# ======================================================================================================================
def test_groq_llama31_70b_returns_valid_first_message():
    filename = os.path.join(llm_config_dir, "groq.json")
    response = check_first_response_is_valid_for_llm_endpoint(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


def test_groq_llama31_70b_uses_external_tool(mock_e2b_api_key_none):
    filename = os.path.join(llm_config_dir, "groq.json")
    response = check_agent_uses_external_tool(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


def test_groq_llama31_70b_recall_chat_memory():
    filename = os.path.join(llm_config_dir, "groq.json")
    response = check_agent_recall_chat_memory(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@retry_until_threshold(threshold=0.75, max_attempts=4)
def test_groq_llama31_70b_archival_memory_retrieval():
    filename = os.path.join(llm_config_dir, "groq.json")
    response = check_agent_archival_memory_retrieval(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


def test_groq_llama31_70b_edit_core_memory():
    filename = os.path.join(llm_config_dir, "groq.json")
    response = check_agent_edit_core_memory(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


# ======================================================================================================================
# GEMINI TESTS
# ======================================================================================================================
@pytest.mark.gemini_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_gemini_pro_15_returns_valid_first_message():
    filename = os.path.join(llm_config_dir, "gemini-pro.json")
    response = check_first_response_is_valid_for_llm_endpoint(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.gemini_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_gemini_pro_15_uses_external_tool(mock_e2b_api_key_none):
    filename = os.path.join(llm_config_dir, "gemini-pro.json")
    response = check_agent_uses_external_tool(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.gemini_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_gemini_pro_15_recall_chat_memory():
    filename = os.path.join(llm_config_dir, "gemini-pro.json")
    response = check_agent_recall_chat_memory(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.gemini_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_gemini_pro_15_archival_memory_retrieval():
    filename = os.path.join(llm_config_dir, "gemini-pro.json")
    response = check_agent_archival_memory_retrieval(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


@pytest.mark.gemini_basic
@retry_until_success(max_attempts=5, sleep_time_seconds=2)
def test_gemini_pro_15_edit_core_memory():
    filename = os.path.join(llm_config_dir, "gemini-pro.json")
    response = check_agent_edit_core_memory(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


# ======================================================================================================================
# TOGETHER TESTS
# ======================================================================================================================
def test_together_llama_3_70b_returns_valid_first_message():
    filename = os.path.join(llm_config_dir, "together-llama-3-70b.json")
    response = check_first_response_is_valid_for_llm_endpoint(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


def test_together_llama_3_70b_uses_external_tool(mock_e2b_api_key_none):
    filename = os.path.join(llm_config_dir, "together-llama-3-70b.json")
    response = check_agent_uses_external_tool(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


def test_together_llama_3_70b_recall_chat_memory():
    filename = os.path.join(llm_config_dir, "together-llama-3-70b.json")
    response = check_agent_recall_chat_memory(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


def test_together_llama_3_70b_archival_memory_retrieval():
    filename = os.path.join(llm_config_dir, "together-llama-3-70b.json")
    response = check_agent_archival_memory_retrieval(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")


def test_together_llama_3_70b_edit_core_memory():
    filename = os.path.join(llm_config_dir, "together-llama-3-70b.json")
    response = check_agent_edit_core_memory(filename)
    # Log out successful response
    print(f"Got successful response from client: \n\n{response}")