# inspecting tools
import importlib
import inspect
import os
import traceback
import warnings
from datetime import datetime
from typing import List, Optional, Tuple, Union

from fastapi import HTTPException

import memgpt.constants as constants
import memgpt.server.utils as server_utils
import memgpt.system as system
from memgpt.agent import Agent, save_agent
from memgpt.agent_store.storage import StorageConnector, TableType
from memgpt.cli.cli_config import get_model_options
from memgpt.config import MemGPTConfig
from memgpt.credentials import MemGPTCredentials
from memgpt.data_sources.connectors import DataConnector, load_data

# from memgpt.data_types import (
#    AgentState,
#    EmbeddingConfig,
#    LLMConfig,
#    Message,
#    Preset,
#    Source,
#    Token,
#    User,
# )
from memgpt.functions.functions import generate_schema, load_function_set

# TODO use custom interface
from memgpt.interface import AgentInterface  # abstract
from memgpt.interface import CLIInterface  # for printing to terminal
from memgpt.log import get_logger
from memgpt.prompts import gpt_system
from memgpt.schemas.agent import AgentState, CreateAgent, UpdateAgentState
from memgpt.schemas.api_key import APIKey, APIKeyCreate
from memgpt.schemas.block import (
    Block,
    CreateBlock,
    CreateHuman,
    CreatePersona,
    UpdateBlock,
)
from memgpt.schemas.document import Document
from memgpt.schemas.embedding_config import EmbeddingConfig

# openai schemas
from memgpt.schemas.enums import JobStatus
from memgpt.schemas.job import Job, JobUpdate
from memgpt.schemas.llm_config import LLMConfig
from memgpt.schemas.memgpt_message import MemGPTMessage
from memgpt.schemas.memory import ArchivalMemorySummary, Memory, RecallMemorySummary
from memgpt.schemas.message import Message, MessageCreate, UpdateMessage
from memgpt.schemas.openai.chat_completion_response import UsageStatistics
from memgpt.schemas.organization import Organization
from memgpt.schemas.passage import Passage
from memgpt.schemas.source import Source, SourceCreate, SourceUpdate
from memgpt.schemas.tool import Tool, ToolCreate, ToolUpdate
from memgpt.schemas.usage import MemGPTUsageStatistics
from memgpt.schemas.user import User, UserCreate
from memgpt.utils import create_random_username, json_dumps, json_loads

# from memgpt.llm_api_tools import openai_get_model_list, azure_openai_get_model_list, smart_urljoin


logger = get_logger(__name__)


# class SyncServer(Server):
#    """Simple single-threaded / blocking server process"""
#
#    def __init__(
#        self,
#        chaining: bool = True,
#        max_chaining_steps: bool = None,
#        default_interface_factory: Callable[[], AgentInterface] = lambda: CLIInterface(),
#        # default_interface: AgentInterface = CLIInterface(),
#        # default_persistence_manager_cls: PersistenceManager = LocalStateManager,
#        # auth_mode: str = "none",  # "none, "jwt", "external"
#    ):
#        """Server process holds in-memory agents that are being run"""
#
#        # List of {'user_id': user_id, 'agent_id': agent_id, 'agent': agent_obj} dicts
#        self.active_agents = []
#
#        # chaining = whether or not to run again if request_heartbeat=true
#        self.chaining = chaining
#
#        # if chaining == true, what's the max number of times we'll chain before yielding?
#        # none = no limit, can go on forever
#        self.max_chaining_steps = max_chaining_steps
#
#        # The default interface that will get assigned to agents ON LOAD
#        self.default_interface_factory = default_interface_factory
#        # self.default_interface = default_interface
#        # self.default_interface = default_interface_cls()
#
#        # Initialize the connection to the DB
#        try:
#            self.config = MemGPTConfig.load()
#            assert self.config.default_llm_config is not None, "default_llm_config must be set in the config"
#            assert self.config.default_embedding_config is not None, "default_embedding_config must be set in the config"
#        except Exception as e:
#            # TODO: very hacky - need to improve model config for docker container
#            if os.getenv("OPENAI_API_KEY") is None:
#                logger.error("No OPENAI_API_KEY environment variable set and no ~/.memgpt/config")
#                raise e
#
#            from memgpt.cli.cli import QuickstartChoice, quickstart
#
#            quickstart(backend=QuickstartChoice.openai, debug=False, terminal=False, latest=False)
#            self.config = MemGPTConfig.load()
#            self.config.save()
#
#        logger.debug(f"loading configuration from '{self.config.config_path}'")
#        assert self.config.persona is not None, "Persona must be set in the config"
#        assert self.config.human is not None, "Human must be set in the config"
#
#        # TODO figure out how to handle credentials for the server
#        self.credentials = MemGPTCredentials.load()
#
#        # Generate default LLM/Embedding configs for the server
#        # TODO: we may also want to do the same thing with default persona/human/etc.
#        self.server_llm_config = LLMConfig(
#            model=self.config.default_llm_config.model,
#            model_endpoint_type=self.config.default_llm_config.model_endpoint_type,
#            model_endpoint=self.config.default_llm_config.model_endpoint,
#            model_wrapper=self.config.default_llm_config.model_wrapper,
#            context_window=self.config.default_llm_config.context_window,
#        )
#        self.server_embedding_config = EmbeddingConfig(
#            embedding_endpoint_type=self.config.default_embedding_config.embedding_endpoint_type,
#            embedding_endpoint=self.config.default_embedding_config.embedding_endpoint,
#            embedding_dim=self.config.default_embedding_config.embedding_dim,
#            embedding_model=self.config.default_embedding_config.embedding_model,
#            embedding_chunk_size=self.config.default_embedding_config.embedding_chunk_size,
#        )
#        assert self.server_embedding_config.embedding_model is not None, vars(self.server_embedding_config)
#
#        # Initialize the metadata store
#        self.ms = MetadataStore(self.config)
#
#        # TODO: this should be removed
#        # add global default tools (for admin)
#        self.add_default_tools(module_name="base")

# TODO: replace all instances of `self`, but using a passed in DB session
# self.ms -> db_session


from collections.abc import Generator

from sqlalchemy.orm import declarative_base

# CRUID methods (Create, Read, Update, Insert, Delete)
from sqlmodel import Session, create_engine

from memgpt.constants import DEFAULT_ORG_ID, DEFAULT_USER_ID

# TODO: eventually import these models from orm/ folder
from memgpt.metadata import (
    AgentModel,
    AgentSourceMappingModel,
    APIKeyModel,
    BlockModel,
    JobModel,
    OrganizationModel,
    PassageModel,
    SourceModel,
    ToolModel,
    UserModel,
)
from memgpt.settings import settings

engine = create_engine(settings.db_uri)
print("ENGINE PATH", settings.db_uri)
Base = declarative_base()


def get_default_llm_config():
    # TODO: move to settings
    config = MemGPTConfig.load()
    return LLMConfig(
        model=config.default_llm_config.model,
        model_endpoint_type=config.default_llm_config.model_endpoint_type,
        model_endpoint=config.default_llm_config.model_endpoint,
        model_wrapper=config.default_llm_config.model_wrapper,
        context_window=config.default_llm_config.context_window,
    )


def get_default_embedding_config():
    # TODO: move to settings
    config = MemGPTConfig.load()
    return EmbeddingConfig(
        embedding_endpoint_type=config.default_embedding_config.embedding_endpoint_type,
        embedding_endpoint=config.default_embedding_config.embedding_endpoint,
        embedding_dim=config.default_embedding_config.embedding_dim,
        embedding_model=config.default_embedding_config.embedding_model,
        embedding_chunk_size=config.default_embedding_config.embedding_chunk_size,
    )


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def generate_default_tool_requests(module_name: str, org_id: str) -> Generator[ToolCreate]:
    """Generate default tool requests from a module"""
    full_module_name = f"memgpt.functions.function_sets.{module_name}"
    try:
        module = importlib.import_module(full_module_name)
    except Exception as e:
        # Handle other general exceptions
        raise e

    try:
        # Load the function set
        functions_to_schema = load_function_set(module)
    except ValueError as e:
        err = f"Error loading function set '{module_name}': {e}"

    # create tool in db
    for name, schema in functions_to_schema.items():
        # print([str(inspect.getsource(line)) for line in schema["imports"]])
        source_code = inspect.getsource(schema["python_function"])
        tags = [module_name]
        if module_name == "base":
            tags.append("memgpt-base")

        # create to tool
        yield ToolCreate(
            name=name,
            tags=tags,
            source_type="python",
            module=schema["module"],
            source_code=source_code,
            json_schema=schema["json_schema"],
            org_id=org_id,
        )


def generate_default_block_requests(org_id: str) -> Generator[Block]:
    """Generate default block requests (default humans/personas)"""
    from memgpt.utils import list_human_files, list_persona_files

    for persona_file in list_persona_files():
        text = open(persona_file, "r", encoding="utf-8").read()
        name = os.path.basename(persona_file).replace(".txt", "")
        yield CreatePersona(org_id=org_id, name=name, value=text, template=True)

    for human_file in list_human_files():
        text = open(human_file, "r", encoding="utf-8").read()
        name = os.path.basename(human_file).replace(".txt", "")
        yield CreateHuman(org_id=org_id, name=name, value=text, template=True)


def init_db(session: Session):
    # TODO: make these into constants
    print("Running init_db")

    # Create all database tables
    Base.metadata.create_all(
        engine,
        tables=[
            UserModel.__table__,
            AgentModel.__table__,
            SourceModel.__table__,
            AgentSourceMappingModel.__table__,
            APIKeyModel.__table__,
            BlockModel.__table__,
            ToolModel.__table__,
            JobModel.__table__,
            OrganizationModel.__table__,
        ],
    )

    # Create the default organization
    """
    Returns a default organization object. This is used in single-user mode to avoid explicit creation of organization and users.
    Both a default organization and default user are created on the database initialization.
    """
    if not session.query(OrganizationModel).filter(OrganizationModel.id == DEFAULT_ORG_ID).scalar():
        # session.add(Organization(id=DEFAULT_ORG_ID).model_dump())
        OrganizationModel(**Organization(id=DEFAULT_ORG_ID).model_dump()).create(session)
        session.commit()

    """
    Returns a default user object. This is used in single-user mode to avoid explicit creation of organization and users.
    The default user is part of the default organization.
    If the BEARER_TOKEN is not set or is an empty string, the default user is used.
    """
    # Create the default user
    if not session.query(UserModel).filter(UserModel.id == DEFAULT_USER_ID).scalar():
        UserModel(**User(id=DEFAULT_USER_ID, org_id=DEFAULT_ORG_ID, name="default").model_dump()).create(session)
        session.commit()

    """
    Add default tools to default user
    """
    for create_tool in generate_default_tool_requests("base", DEFAULT_ORG_ID):
        tool = ToolModel(**Tool(**create_tool.model_dump()).model_dump()).create(session)
        session.commit()
        print(f"Created tool: {tool}")

    """
    Add default blocks to default user
    """
    for create_block in generate_default_block_requests(DEFAULT_ORG_ID):
        block = BlockModel(**Block(**create_block.model_dump()).model_dump()).create(session)
        session.commit()
        print(f"Created block: {block}")


## ORGANIZATION

from typing import Callable

# TODO: users must be created with an organizaiton, or be added to a default organization
from memgpt.settings import Settings


class Server:
    """
    Server object that does *not* hold any state (all state is persisted in the DB) other than settings and the interface.
    """

    def __init__(
        self,
        settings: Settings = Settings(),
        interface_factory: Callable[[], AgentInterface] = lambda: CLIInterface(),
    ):
        self.settings = settings
        self.default_interface_factory = interface_factory

    def init_organization_data(self, session: Session, org_id: str):
        # TODO: add default blocks (humans/personas)
        # TODO: add default tools
        pass

    def get_organization(self, session: Session, user_id: str) -> Organization:
        org_id = UserModel.read(session, user_id).org_id
        return OrganizationModel.read(session, org_id)

    def list_organizations(self, session: Session, filters, cursor: str, limit: int) -> List[Organization]:
        pass

    def create_organization(self, session: Session) -> Organization:
        pass

    ## USERS
    def create_user(self, session: Session, request: UserCreate) -> User:
        pass

    def get_user(self, session: Session, user_id: str) -> User:
        pass

    def update_user(self, session: Session, user_id: str, request: UserCreate) -> User:
        pass

    def delete_user(self, session: Session, user_id: str) -> User:
        pass

    def list_users(self, session: Session, org_id: str, filters, cursor: str, limit: int) -> List[User]:
        pass

    def get_user_id(self, session: Session, org_id: str, name: str) -> str:
        pass

    ## AGENTS

    # TODO: should user_org id instead of user_id eventually
    def create_agent(self, session: Session, request: CreateAgent, user_id: str) -> AgentState:
        # TODO: check if the name is already created in the org?

        """Create a new agent"""
        org_id = self.get_organization(session, user_id).id
        print("User ID", user_id, org_id)

        # create default interface
        interface = self.default_interface_factory()

        # create agent name
        if request.name is None:
            request.name = create_random_username()

        # system debug
        if request.system is None:
            # TODO: don't hardcode
            request.system = gpt_system.get_system_text("memgpt_chat")

        if request.llm_config is None:
            request.llm_config = get_default_llm_config()

        if request.embedding_config is None:
            request.embedding_config = get_default_embedding_config()

        # get tools and make sure they exist
        tool_objs = []
        if request.tools:
            for tool_name in request.tools:
                tool_obj = ToolModel.read_by_name(session, tool_name)
                assert tool_obj, f"Tool {tool_name} does not exist"
                tool_objs.append(tool_obj.to_record())

        # save agent
        agent_state = AgentState(
            name=request.name,
            org_id=org_id,
            tools=request.tools,  # name=id for tools
            llm_config=request.llm_config,
            embedding_config=request.embedding_config,
            system=request.system,
            memory=request.memory,
            description=request.description,
            metadata_=request.metadata_,
            user_id=user_id,
        )

        try:

            agent = Agent(
                interface=interface,
                agent_state=agent_state,
                tools=tool_objs,
                # gpt-3.5-turbo tends to omit inner monologue, relax this requirement for now
                first_message_verify_mono=(
                    True if (agent_state.llm_config.model is not None and "gpt-4" in agent_state.llm_config.model) else False
                ),
            )
            # rebuilding agent memory on agent create in case shared memory blocks
            # were specified in the new agent's memory config. we're doing this for two reasons:
            # 1. if only the ID of the shared memory block was specified, we can fetch its most recent value
            # 2. if the shared block state changed since this agent initialization started, we can be sure to have the latest value
            agent.rebuild_memory(force=True)
            # FIXME: this is a hacky way to get the system prompts injected into agent into the DB
            # self.ms.update_agent(agent.agent_state)
        except Exception as e:
            logger.exception(e)
            try:
                if agent:
                    self.delete_agent(session, agent.agent_state.id)
            except Exception as delete_e:
                logger.exception(f"Failed to delete_agent:\n{delete_e}")
            raise e

        # save agent with any state updatess
        AgentModel(**agent.agent_state.model_dump()).create(session)
        logger.info(f"Created new agent from config: {agent}")

        assert isinstance(agent.agent_state.memory, Memory), f"Invalid memory type: {type(agent_state.memory)}"
        # return AgentState
        return agent.agent_state

    def load_agent(self, session: Session, agent_id: str) -> Agent:
        """
        Loads an instantiated `Agent` class.

        Args:
            session (Session): The DB session object

        Returns:
            agent (Agent): The instantiated agent object
        """
        agent_state = AgentState.read(session, agent_id)  # TODO: implement
        if not agent_state:
            raise ValueError(f"Agent does not exist")

        # gather tool objects
        # TODO: eventually just place this in `AgentState`
        tools = []
        for tool_name in agent_state.tools:
            tool_obj = ToolModel.read_by_name(session, tool_name)  # TODO: implement this
            if not tool_obj:
                raise ValueError(f"Tool {tool_name} does not exist")
            tools.append(tool_obj)

        return Agent(
            interface=self.default_interface_factory(),
            tools=tools,
            agent_state=agent_state,
        )

    def get_agent(self, session: Session, agent_id: str) -> AgentState:
        return session.query(AgentModel).filter(AgentModel.id == agent_id).scalar()

    def update_agent(self, session: Session, agent_id: str, request: UpdateAgentState) -> AgentState:
        pass

    def delete_agent(self, session: Session, agent_id: str) -> AgentState:
        return AgentModel.delete(session, agent_id)

    def list_agents(self, session: Session, org_id: str, filters, cursor: str, limit: int) -> List[AgentState]:
        # TODO: add org_id?
        pass

    def get_agent_id(self, session: Session, org_id: str, name: str) -> str:
        # TODO: add org_id?
        pass

    def get_archival_memory_summary(self, session: Session, agent_id: str) -> ArchivalMemorySummary:
        pass

    def get_recall_memory_summary(self, session: Session, agent_id: str) -> RecallMemorySummary:
        pass

    ## TOOLS

    def create_tool(self, session: Session, request: ToolCreate) -> Tool:
        pass

    def get_tool(self, session: Session, tool_id: str) -> Tool:
        pass

    def update_tool(self, session: Session, tool_id: str, request: ToolUpdate) -> Tool:
        pass

    def delete_tool(self, session: Session, tool_id: str) -> Tool:
        pass

    def list_tools(self, session: Session, org_id: str, filters, cursor: str, limit: int) -> List[Tool]:
        pass

    def get_tool_id(self, session: Session, org_id: str, name: str) -> str:
        pass

    ## SOURCES

    def create_source(self, session: Session, request: SourceCreate) -> Source:
        pass

    def get_source(self, session: Session, source_id: str) -> Source:
        pass

    def update_source(self, session: Session, source_id: str, request: SourceUpdate) -> Source:
        pass

    def delete_source(self, session: Session, source_id: str) -> Source:
        pass

    def list_sources(self, session: Session, org_id: str, filters, cursor: str, limit: int) -> List[Source]:
        pass

    def get_source_id(self, session: Session, org_id: str, name: str) -> str:
        pass

    ## JOBS

    def create_job(self, session: Session) -> Job:
        # This simply creates a job with the status CREATED
        pass

    def get_job(self, session: Session, job_id: str) -> Job:
        pass

    def update_job(self, session: Session, job_id: str, request: JobUpdate) -> Job:
        pass

    ## DATA LOADING

    def load_data(self, session: Session, connector: DataConnector, source_id: str) -> List[Document]:
        pass

    ## BLOCKS

    def create_block(self, session: Session, request: CreateBlock) -> Block:
        pass

    def get_block(self, session: Session, block_id: str) -> Block:
        pass

    def update_block(self, session: Session, block_id: str, request: UpdateBlock) -> Block:
        pass

    def delete_block(self, session: Session, block_id: str) -> Block:
        pass

    def list_blocks(self, session: Session, org_id: str, filters, cursor: str, limit: int) -> List[Block]:
        pass

    ## MESSAGES (Note: called from `Agent`)

    def create_message(self, session: Session, request: MessageCreate) -> Message:
        pass

    def get_message(self, session: Session, message_id: str) -> Message:
        pass

    def update_message(self, session: Session, message_id: str, request: UpdateMessage) -> Message:
        pass

    def list_messages(self, session: Session, filters, cursor: str, limit: int) -> List[Message]:
        pass

    def query_messages_text(self, session: Session, query: str, filters) -> List[Message]:
        # TODO: filters should include agent_id
        pass

    def query_messages_date(self, session: Session, query: str, filters) -> List[Message]:
        pass

    ## PASSAGES (Note: called from `Agent`)

    def create_passage(self, session: Session, request: Passage) -> Passage:
        pass

    def get_passage(self, session: Session, passage_id: str) -> Passage:
        return session.query(PassageModel).filter(PassageModel.id == passage_id).scalar()

    def list_passages(self, session: Session, filters, cursor: str, limit: int) -> List[Passage]:
        # TODO: filters should filter by either the source_id or agent_id
        pass

    def query_passages_vector(self, session: Session, query: str, filters) -> List[Passage]:
        # TODO: filters should filter by either the source_id or agent_id
        pass

    ## CONFIGS

    def list_llm_configs(self, session: Session, org_id: str) -> List[LLMConfig]:
        pass

    def list_embedding_configs(self, session: Session, org_id: str) -> List[EmbeddingConfig]:
        pass

    ## ORGNIZATION  (TODO: do last)

    # def create_organization(session: Session, request: OrganizationCreate) -> Organization:
    #    pass
    #
    # def get_organization(session: Session, org_id: str) -> Organization:
    #    pass
    #
    # def update_organization(session: Session, org_id: str, request: OrganizationUpdate) -> Organization:
    #    pass
    #
    # def delete_organization(session: Session, org_id: str) -> Organization:
    #    pass

    # More advanced private methods


def _load_agent(self, user_id: str, agent_id: str, interface: Union[AgentInterface, None] = None) -> Agent:
    """Loads a saved agent into memory (if it doesn't exist, throw an error)"""
    assert isinstance(user_id, str), user_id
    assert isinstance(agent_id, str), agent_id

    # If an interface isn't specified, use the default
    if interface is None:
        interface = self.default_interface_factory()

    try:
        logger.info(f"Grabbing agent user_id={user_id} agent_id={agent_id} from database")
        agent_state = self.ms.get_agent(agent_id=agent_id, user_id=user_id)
        if not agent_state:
            logger.exception(f"agent_id {agent_id} does not exist")
            raise ValueError(f"agent_id {agent_id} does not exist")

        # Instantiate an agent object using the state retrieved
        logger.info(f"Creating an agent object")
        tool_objs = []
        for name in agent_state.tools:
            tool_obj = self.ms.get_tool(tool_name=name, user_id=user_id)
            if not tool_obj:
                logger.exception(f"Tool {name} does not exist for user {user_id}")
                raise ValueError(f"Tool {name} does not exist for user {user_id}")
            tool_objs.append(tool_obj)

        # Make sure the memory is a memory object
        assert isinstance(agent_state.memory, Memory)

        memgpt_agent = Agent(agent_state=agent_state, interface=interface, tools=tool_objs)

        # Add the agent to the in-memory store and return its reference
        logger.info(f"Adding agent to the agent cache: user_id={user_id}, agent_id={agent_id}")
        self._add_agent(user_id=user_id, agent_id=agent_id, agent_obj=memgpt_agent)
        return memgpt_agent

    except Exception as e:
        logger.exception(f"Error occurred while trying to get agent {agent_id}:\n{e}")
        raise


def _get_or_load_agent(self, agent_id: str) -> Agent:
    """Check if the agent is in-memory, then load"""
    agent_state = self.ms.get_agent(agent_id=agent_id)
    if not agent_state:
        raise ValueError(f"Agent does not exist")
    user_id = agent_state.user_id

    logger.debug(f"Checking for agent user_id={user_id} agent_id={agent_id}")
    # TODO: consider disabling loading cached agents due to potential concurrency issues
    memgpt_agent = self._get_agent(user_id=user_id, agent_id=agent_id)
    if not memgpt_agent:
        logger.debug(f"Agent not loaded, loading agent user_id={user_id} agent_id={agent_id}")
        memgpt_agent = self._load_agent(user_id=user_id, agent_id=agent_id)
    return memgpt_agent


def _step(self, user_id: str, agent_id: str, input_message: Union[str, Message], timestamp: Optional[datetime]) -> MemGPTUsageStatistics:
    """Send the input message through the agent"""
    logger.debug(f"Got input message: {input_message}")
    try:

        # Get the agent object (loaded in memory)
        memgpt_agent = self._get_or_load_agent(agent_id=agent_id)
        if memgpt_agent is None:
            raise KeyError(f"Agent (user={user_id}, agent={agent_id}) is not loaded")

        # Determine whether or not to token stream based on the capability of the interface
        token_streaming = memgpt_agent.interface.streaming_mode if hasattr(memgpt_agent.interface, "streaming_mode") else False

        logger.debug(f"Starting agent step")
        no_verify = True
        next_input_message = input_message
        counter = 0
        total_usage = UsageStatistics()
        step_count = 0
        while True:
            new_messages, heartbeat_request, function_failed, token_warning, usage = memgpt_agent.step(
                next_input_message,
                first_message=False,
                skip_verify=no_verify,
                return_dicts=False,
                stream=token_streaming,
                timestamp=timestamp,
                ms=self.ms,
            )
            step_count += 1
            total_usage += usage
            counter += 1
            memgpt_agent.interface.step_complete()

            logger.debug("Saving agent state")
            # save updated state
            save_agent(memgpt_agent, self.ms)

            # Chain stops
            if not self.chaining:
                logger.debug("No chaining, stopping after one step")
                break
            elif self.max_chaining_steps is not None and counter > self.max_chaining_steps:
                logger.debug(f"Hit max chaining steps, stopping after {counter} steps")
                break
            # Chain handlers
            elif token_warning:
                next_input_message = system.get_token_limit_warning()
                continue  # always chain
            elif function_failed:
                next_input_message = system.get_heartbeat(constants.FUNC_FAILED_HEARTBEAT_MESSAGE)
                continue  # always chain
            elif heartbeat_request:
                next_input_message = system.get_heartbeat(constants.REQ_HEARTBEAT_MESSAGE)
                continue  # always chain
            # MemGPT no-op / yield
            else:
                break

    except Exception as e:
        logger.error(f"Error in server._step: {e}")
        print(traceback.print_exc())
        raise
    finally:
        logger.debug("Calling step_yield()")
        memgpt_agent.interface.step_yield()

    return MemGPTUsageStatistics(**total_usage.dict(), step_count=step_count)


def _command(self, user_id: str, agent_id: str, command: str) -> MemGPTUsageStatistics:
    """Process a CLI command"""

    logger.debug(f"Got command: {command}")

    # Get the agent object (loaded in memory)
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)
    usage = None

    if command.lower() == "exit":
        # exit not supported on server.py
        raise ValueError(command)

    elif command.lower() == "save" or command.lower() == "savechat":
        save_agent(memgpt_agent, self.ms)

    elif command.lower() == "attach":
        # Different from CLI, we extract the data source name from the command
        command = command.strip().split()
        try:
            data_source = int(command[1])
        except:
            raise ValueError(command)

        # attach data to agent from source
        source_connector = StorageConnector.get_storage_connector(TableType.PASSAGES, self.config, user_id=user_id)
        memgpt_agent.attach_source(data_source, source_connector, self.ms)

    elif command.lower() == "dump" or command.lower().startswith("dump "):
        # Check if there's an additional argument that's an integer
        command = command.strip().split()
        amount = int(command[1]) if len(command) > 1 and command[1].isdigit() else 0
        if amount == 0:
            memgpt_agent.interface.print_messages(memgpt_agent.messages, dump=True)
        else:
            memgpt_agent.interface.print_messages(memgpt_agent.messages[-min(amount, len(memgpt_agent.messages)) :], dump=True)

    elif command.lower() == "dumpraw":
        memgpt_agent.interface.print_messages_raw(memgpt_agent.messages)

    elif command.lower() == "memory":
        ret_str = (
            f"\nDumping memory contents:\n"
            + f"\n{str(memgpt_agent.memory)}"
            + f"\n{str(memgpt_agent.persistence_manager.archival_memory)}"
            + f"\n{str(memgpt_agent.persistence_manager.recall_memory)}"
        )
        return ret_str

    elif command.lower() == "pop" or command.lower().startswith("pop "):
        # Check if there's an additional argument that's an integer
        command = command.strip().split()
        pop_amount = int(command[1]) if len(command) > 1 and command[1].isdigit() else 3
        n_messages = len(memgpt_agent.messages)
        MIN_MESSAGES = 2
        if n_messages <= MIN_MESSAGES:
            logger.info(f"Agent only has {n_messages} messages in stack, none left to pop")
        elif n_messages - pop_amount < MIN_MESSAGES:
            logger.info(f"Agent only has {n_messages} messages in stack, cannot pop more than {n_messages - MIN_MESSAGES}")
        else:
            logger.info(f"Popping last {pop_amount} messages from stack")
            for _ in range(min(pop_amount, len(memgpt_agent.messages))):
                memgpt_agent.messages.pop()

    elif command.lower() == "retry":
        # TODO this needs to also modify the persistence manager
        logger.info(f"Retrying for another answer")
        while len(memgpt_agent.messages) > 0:
            if memgpt_agent.messages[-1].get("role") == "user":
                # we want to pop up to the last user message and send it again
                memgpt_agent.messages[-1].get("content")
                memgpt_agent.messages.pop()
                break
            memgpt_agent.messages.pop()

    elif command.lower() == "rethink" or command.lower().startswith("rethink "):
        # TODO this needs to also modify the persistence manager
        if len(command) < len("rethink "):
            logger.warning("Missing text after the command")
        else:
            for x in range(len(memgpt_agent.messages) - 1, 0, -1):
                if memgpt_agent.messages[x].get("role") == "assistant":
                    text = command[len("rethink ") :].strip()
                    memgpt_agent.messages[x].update({"content": text})
                    break

    elif command.lower() == "rewrite" or command.lower().startswith("rewrite "):
        # TODO this needs to also modify the persistence manager
        if len(command) < len("rewrite "):
            logger.warning("Missing text after the command")
        else:
            for x in range(len(memgpt_agent.messages) - 1, 0, -1):
                if memgpt_agent.messages[x].get("role") == "assistant":
                    text = command[len("rewrite ") :].strip()
                    args = json_loads(memgpt_agent.messages[x].get("function_call").get("arguments"))
                    args["message"] = text
                    memgpt_agent.messages[x].get("function_call").update({"arguments": json_dumps(args)})
                    break

    # No skip options
    elif command.lower() == "wipe":
        # exit not supported on server.py
        raise ValueError(command)

    elif command.lower() == "heartbeat":
        input_message = system.get_heartbeat()
        usage = self._step(user_id=user_id, agent_id=agent_id, input_message=input_message)

    elif command.lower() == "memorywarning":
        input_message = system.get_token_limit_warning()
        usage = self._step(user_id=user_id, agent_id=agent_id, input_message=input_message)

    if not usage:
        usage = MemGPTUsageStatistics()

    return usage


def user_message(
    self,
    user_id: str,
    agent_id: str,
    message: Union[str, Message],
    timestamp: Optional[datetime] = None,
) -> MemGPTUsageStatistics:
    """Process an incoming user message and feed it through the MemGPT agent"""
    if self.ms.get_user(user_id=user_id) is None:
        raise ValueError(f"User user_id={user_id} does not exist")
    if self.ms.get_agent(agent_id=agent_id, user_id=user_id) is None:
        raise ValueError(f"Agent agent_id={agent_id} does not exist")

    # Basic input sanitization
    if isinstance(message, str):
        if len(message) == 0:
            raise ValueError(f"Invalid input: '{message}'")

        # If the input begins with a command prefix, reject
        elif message.startswith("/"):
            raise ValueError(f"Invalid input: '{message}'")

        packaged_user_message = system.package_user_message(
            user_message=message,
            time=timestamp.isoformat() if timestamp else None,
        )

        # NOTE: eventually deprecate and only allow passing Message types
        # Convert to a Message object
        if timestamp:
            message = Message(
                user_id=user_id,
                agent_id=agent_id,
                role="user",
                text=packaged_user_message,
                created_at=timestamp,
            )
        else:
            message = Message(
                user_id=user_id,
                agent_id=agent_id,
                role="user",
                text=packaged_user_message,
            )

    # Run the agent state forward
    usage = self._step(user_id=user_id, agent_id=agent_id, input_message=packaged_user_message, timestamp=timestamp)
    return usage


def system_message(
    self,
    user_id: str,
    agent_id: str,
    message: Union[str, Message],
    timestamp: Optional[datetime] = None,
) -> MemGPTUsageStatistics:
    """Process an incoming system message and feed it through the MemGPT agent"""
    if self.ms.get_user(user_id=user_id) is None:
        raise ValueError(f"User user_id={user_id} does not exist")
    if self.ms.get_agent(agent_id=agent_id, user_id=user_id) is None:
        raise ValueError(f"Agent agent_id={agent_id} does not exist")

    # Basic input sanitization
    if isinstance(message, str):
        if len(message) == 0:
            raise ValueError(f"Invalid input: '{message}'")

        # If the input begins with a command prefix, reject
        elif message.startswith("/"):
            raise ValueError(f"Invalid input: '{message}'")

        packaged_system_message = system.package_system_message(system_message=message)

        # NOTE: eventually deprecate and only allow passing Message types
        # Convert to a Message object

        if timestamp:
            message = Message(
                user_id=user_id,
                agent_id=agent_id,
                role="system",
                text=packaged_system_message,
                created_at=timestamp,
            )
        else:
            message = Message(
                user_id=user_id,
                agent_id=agent_id,
                role="system",
                text=packaged_system_message,
            )

    if isinstance(message, Message):
        # Can't have a null text field
        if len(message.text) == 0 or message.text is None:
            raise ValueError(f"Invalid input: '{message.text}'")
        # If the input begins with a command prefix, reject
        elif message.text.startswith("/"):
            raise ValueError(f"Invalid input: '{message.text}'")

    else:
        raise TypeError(f"Invalid input: '{message}' - type {type(message)}")

    if timestamp:
        # Override the timestamp with what the caller provided
        message.created_at = timestamp

    # Run the agent state forward
    return self._step(user_id=user_id, agent_id=agent_id, input_message=packaged_system_message, timestamp=timestamp)


# @LockingServer.agent_lock_decorator
def run_command(self, user_id: str, agent_id: str, command: str) -> MemGPTUsageStatistics:
    """Run a command on the agent"""
    if self.ms.get_user(user_id=user_id) is None:
        raise ValueError(f"User user_id={user_id} does not exist")
    if self.ms.get_agent(agent_id=agent_id, user_id=user_id) is None:
        raise ValueError(f"Agent agent_id={agent_id} does not exist")

    # If the input begins with a command prefix, attempt to process it as a command
    if command.startswith("/"):
        if len(command) > 1:
            command = command[1:]  # strip the prefix
    return self._command(user_id=user_id, agent_id=agent_id, command=command)


def list_users_paginated(self, cursor: str, limit: int) -> List[User]:
    """List all users"""
    # TODO: make this paginated
    next_cursor, users = self.ms.get_all_users(cursor, limit)
    return next_cursor, users


def create_user(self, request: UserCreate) -> User:
    """Create a new user using a config"""
    if not request.name:
        # auto-generate a name
        request.name = create_random_username()
    user = User(name=request.name)
    self.ms.create_user(user)
    logger.info(f"Created new user from config: {user}")

    # add default for the user
    assert user.id is not None, f"User id is None: {user}"
    self.add_default_blocks(user.id)
    self.add_default_tools(module_name="base", user_id=user.id)

    return user


def create_agent_legacy(
    self,
    request: CreateAgent,
    user_id: str,
    # interface
    interface: Union[AgentInterface, None] = None,
) -> AgentState:
    """Create a new agent using a config"""
    if self.ms.get_user(user_id=user_id) is None:
        raise ValueError(f"User user_id={user_id} does not exist")

    if interface is None:
        interface = self.default_interface_factory()

    # create agent name
    if request.name is None:
        request.name = create_random_username()

    # system debug
    if request.system is None:
        # TODO: don't hardcode
        request.system = gpt_system.get_system_text("memgpt_chat")

    logger.debug(f"Attempting to find user: {user_id}")
    user = self.ms.get_user(user_id=user_id)
    if not user:
        raise ValueError(f"cannot find user with associated client id: {user_id}")

    try:
        # model configuration
        llm_config = request.llm_config if request.llm_config else self.server_llm_config
        embedding_config = request.embedding_config if request.embedding_config else self.server_embedding_config

        # get tools + make sure they exist
        tool_objs = []
        for tool_name in request.tools:
            tool_obj = self.ms.get_tool(tool_name=tool_name, user_id=user_id)
            assert tool_obj, f"Tool {tool_name} does not exist"
            tool_objs.append(tool_obj)

        # TODO: save the agent state
        agent_state = AgentState(
            name=request.name,
            user_id=user_id,
            tools=request.tools,  # name=id for tools
            llm_config=llm_config,
            embedding_config=embedding_config,
            system=request.system,
            memory=request.memory,
            description=request.description,
            metadata_=request.metadata_,
        )
        agent = Agent(
            interface=interface,
            agent_state=agent_state,
            tools=tool_objs,
            # gpt-3.5-turbo tends to omit inner monologue, relax this requirement for now
            first_message_verify_mono=True if (llm_config.model is not None and "gpt-4" in llm_config.model) else False,
        )
        # rebuilding agent memory on agent create in case shared memory blocks
        # were specified in the new agent's memory config. we're doing this for two reasons:
        # 1. if only the ID of the shared memory block was specified, we can fetch its most recent value
        # 2. if the shared block state changed since this agent initialization started, we can be sure to have the latest value
        agent.rebuild_memory(force=True, ms=self.ms)
        # FIXME: this is a hacky way to get the system prompts injected into agent into the DB
        # self.ms.update_agent(agent.agent_state)
    except Exception as e:
        logger.exception(e)
        try:
            if agent:
                self.ms.delete_agent(agent_id=agent.agent_state.id)
        except Exception as delete_e:
            logger.exception(f"Failed to delete_agent:\n{delete_e}")
        raise e

    # save agent
    save_agent(agent, self.ms)
    logger.info(f"Created new agent from config: {agent}")

    assert isinstance(agent.agent_state.memory, Memory), f"Invalid memory type: {type(agent_state.memory)}"
    # return AgentState
    return agent.agent_state


def update_agent(
    self,
    request: UpdateAgentState,
    user_id: str,
):
    """Update the agents core memory block, return the new state"""
    if self.ms.get_user(user_id=user_id) is None:
        raise ValueError(f"User user_id={user_id} does not exist")
    if self.ms.get_agent(agent_id=request.id) is None:
        raise ValueError(f"Agent agent_id={request.id} does not exist")

    # Get the agent object (loaded in memory)
    memgpt_agent = self._get_or_load_agent(agent_id=request.id)

    # update the core memory of the agent
    if request.memory:
        assert isinstance(request.memory, Memory), type(request.memory)
        new_memory_contents = request.memory.to_flat_dict()
        _ = self.update_agent_core_memory(user_id=user_id, agent_id=request.id, new_memory_contents=new_memory_contents)

    # update the system prompt
    if request.system:
        memgpt_agent.update_system_prompt(request.system)

    # update in-context messages
    if request.message_ids:
        # This means the user is trying to change what messages are in the message buffer
        # Internally this requires (1) pulling from recall,
        # then (2) setting the attributes ._messages and .state.message_ids
        memgpt_agent.set_message_buffer(message_ids=request.message_ids)

    # tools
    if request.tools:
        # Replace tools and also re-link

        # (1) get tools + make sure they exist
        tool_objs = []
        for tool_name in request.tools:
            tool_obj = self.ms.get_tool(tool_name=tool_name, user_id=user_id)
            assert tool_obj, f"Tool {tool_name} does not exist"
            tool_objs.append(tool_obj)

        # (2) replace the list of tool names ("ids") inside the agent state
        memgpt_agent.agent_state.tools = request.tools

        # (3) then attempt to link the tools modules
        memgpt_agent.link_tools(tool_objs)

    # configs
    if request.llm_config:
        memgpt_agent.agent_state.llm_config = request.llm_config
    if request.embedding_config:
        memgpt_agent.agent_state.embedding_config = request.embedding_config

    # other minor updates
    if request.name:
        memgpt_agent.agent_state.name = request.name
    if request.metadata_:
        memgpt_agent.agent_state.metadata_ = request.metadata_

    # save the agent
    assert isinstance(memgpt_agent.memory, Memory)
    save_agent(memgpt_agent, self.ms)
    # TODO: probably reload the agent somehow?
    return memgpt_agent.agent_state


def _agent_state_to_config(self, agent_state: AgentState) -> dict:
    """Convert AgentState to a dict for a JSON response"""
    assert agent_state is not None

    agent_config = {
        "id": agent_state.id,
        "name": agent_state.name,
        "human": agent_state._metadata.get("human", None),
        "persona": agent_state._metadata.get("persona", None),
        "created_at": agent_state.created_at.isoformat(),
    }
    return agent_config


def list_agents(
    self,
    user_id: str,
) -> List[AgentState]:
    """List all available agents to a user"""
    if self.ms.get_user(user_id=user_id) is None:
        raise ValueError(f"User user_id={user_id} does not exist")

    agents_states = self.ms.list_agents(user_id=user_id)
    return agents_states


# TODO make return type pydantic
def list_agents_legacy(
    self,
    user_id: str,
) -> dict:
    """List all available agents to a user"""

    if user_id is None:
        agents_states = self.ms.list_all_agents()
    else:
        if self.ms.get_user(user_id=user_id) is None:
            raise ValueError(f"User user_id={user_id} does not exist")

        agents_states = self.ms.list_agents(user_id=user_id)

    agents_states_dicts = [self._agent_state_to_config(state) for state in agents_states]

    # TODO add a get_message_obj_from_message_id(...) function
    #      this would allow grabbing Message.created_by without having to load the agent object
    # all_available_tools = self.ms.list_tools(user_id=user_id) # TODO: add back when user-specific
    self.ms.list_tools()

    for agent_state, return_dict in zip(agents_states, agents_states_dicts):

        # Get the agent object (loaded in memory)
        memgpt_agent = self._get_or_load_agent(user_id=agent_state.user_id, agent_id=agent_state.id)

        # TODO remove this eventually when return type get pydanticfied
        # this is to add persona_name and human_name so that the columns in UI can populate
        # TODO hack for frontend, remove
        # (top level .persona is persona_name, and nested memory.persona is the state)
        # TODO: eventually modify this to be contained in the metadata
        return_dict["persona"] = agent_state._metadata.get("persona", None)
        return_dict["human"] = agent_state._metadata.get("human", None)

        # Add information about tools
        # TODO memgpt_agent should really have a field of List[ToolModel]
        #      then we could just pull that field and return it here
        # return_dict["tools"] = [tool for tool in all_available_tools if tool.json_schema in memgpt_agent.functions]

        # get tool info from agent state
        tools = []
        for tool_name in agent_state.tools:
            tool = self.ms.get_tool(tool_name=tool_name, user_id=user_id)
            tools.append(tool)
        return_dict["tools"] = tools

        # Add information about memory (raw core, size of recall, size of archival)
        core_memory = memgpt_agent.memory
        recall_memory = memgpt_agent.persistence_manager.recall_memory
        archival_memory = memgpt_agent.persistence_manager.archival_memory
        memory_obj = {
            "core_memory": core_memory.to_flat_dict(),
            "recall_memory": len(recall_memory) if recall_memory is not None else None,
            "archival_memory": len(archival_memory) if archival_memory is not None else None,
        }
        return_dict["memory"] = memory_obj

        # Add information about last run
        # NOTE: 'last_run' is just the timestamp on the latest message in the buffer
        # Retrieve the Message object via the recall storage or by directly access _messages
        last_msg_obj = memgpt_agent._messages[-1]
        return_dict["last_run"] = last_msg_obj.created_at

        # Add information about attached sources
        sources_ids = self.ms.list_attached_sources(agent_id=agent_state.id)
        sources = [self.ms.get_source(source_id=s_id) for s_id in sources_ids]
        return_dict["sources"] = [vars(s) for s in sources]

    # Sort agents by "last_run" in descending order, most recent first
    agents_states_dicts.sort(key=lambda x: x["last_run"], reverse=True)

    logger.debug(f"Retrieved {len(agents_states)} agents for user {user_id}")
    return {
        "num_agents": len(agents_states),
        "agents": agents_states_dicts,
    }


# blocks


def get_blocks(
    self,
    user_id: Optional[str] = None,
    label: Optional[str] = None,
    template: bool = True,
    name: Optional[str] = None,
    id: Optional[str] = None,
) -> Optional[List[Block]]:

    return self.ms.get_blocks(user_id=user_id, label=label, template=template, name=name, id=id)


def get_block(self, block_id: str):

    blocks = self.get_blocks(id=block_id)
    if blocks is None or len(blocks) == 0:
        raise ValueError("Block does not exist")
    if len(blocks) > 1:
        raise ValueError("Multiple blocks with the same id")
    return blocks[0]


def create_block(self, request: CreateBlock, user_id: str, update: bool = False) -> Block:
    existing_blocks = self.ms.get_blocks(name=request.name, user_id=user_id, template=request.template, label=request.label)
    if existing_blocks is not None:
        existing_block = existing_blocks[0]
        assert len(existing_blocks) == 1
        if update:
            return self.update_block(UpdateBlock(id=existing_block.id, **vars(request)), user_id)
        else:
            raise ValueError(f"Block with name {request.name} already exists")
    block = Block(**vars(request))
    self.ms.create_block(block)
    return block


def update_block(self, request: UpdateBlock) -> Block:
    block = self.get_block(request.id)
    block.limit = request.limit if request.limit is not None else block.limit
    block.value = request.value if request.value is not None else block.value
    block.name = request.name if request.name is not None else block.name
    self.ms.update_block(block=block)
    return block


def delete_block(self, block_id: str):
    block = self.get_block(block_id)
    self.ms.delete_block(block_id)
    return block


# convert name->id


def get_agent_id(self, name: str, user_id: str):
    agent_state = self.ms.get_agent(agent_name=name, user_id=user_id)
    if not agent_state:
        return None
    return agent_state.id


def get_source(self, source_id: str, user_id: str) -> Source:
    existing_source = self.ms.get_source(source_id=source_id, user_id=user_id)
    if not existing_source:
        raise ValueError("Source does not exist")
    return existing_source


def get_source_id(self, source_name: str, user_id: str) -> str:
    existing_source = self.ms.get_source(source_name=source_name, user_id=user_id)
    if not existing_source:
        raise ValueError("Source does not exist")
    return existing_source.id


def get_agent(self, user_id: str, agent_id: str, agent_name: Optional[str] = None):
    """Get the agent state"""
    return self.ms.get_agent(agent_id=agent_id, user_id=user_id)


def get_user(self, user_id: str) -> User:
    """Get the user"""
    return self.ms.get_user(user_id=user_id)


def get_agent_memory(self, agent_id: str) -> Memory:
    """Return the memory of an agent (core memory)"""
    agent = self._get_or_load_agent(agent_id=agent_id)
    return agent.memory


def get_archival_memory_summary(self, agent_id: str) -> ArchivalMemorySummary:
    agent = self._get_or_load_agent(agent_id=agent_id)
    return ArchivalMemorySummary(size=len(agent.persistence_manager.archival_memory))


def get_recall_memory_summary(self, agent_id: str) -> RecallMemorySummary:
    agent = self._get_or_load_agent(agent_id=agent_id)
    return RecallMemorySummary(size=len(agent.persistence_manager.recall_memory))


def get_in_context_message_ids(self, agent_id: str) -> List[str]:
    """Get the message ids of the in-context messages in the agent's memory"""
    # Get the agent object (loaded in memory)
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)
    return [m.id for m in memgpt_agent._messages]


def get_in_context_messages(self, agent_id: str) -> List[Message]:
    """Get the in-context messages in the agent's memory"""
    # Get the agent object (loaded in memory)
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)
    return memgpt_agent._messages


def get_agent_message(self, agent_id: str, message_id: str) -> Message:
    """Get a single message from the agent's memory"""
    # Get the agent object (loaded in memory)
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)
    message = memgpt_agent.persistence_manager.recall_memory.storage.get(id=message_id)
    return message


def get_agent_messages(
    self,
    agent_id: str,
    start: int,
    count: int,
    return_message_object: bool = True,
) -> Union[List[Message], List[MemGPTMessage]]:
    """Paginated query of all messages in agent message queue"""
    # Get the agent object (loaded in memory)
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)

    if start < 0 or count < 0:
        raise ValueError("Start and count values should be non-negative")

    if start + count < len(memgpt_agent._messages):  # messages can be returned from whats in memory
        # Reverse the list to make it in reverse chronological order
        reversed_messages = memgpt_agent._messages[::-1]
        # Check if start is within the range of the list
        if start >= len(reversed_messages):
            raise IndexError("Start index is out of range")

        # Calculate the end index, ensuring it does not exceed the list length
        end_index = min(start + count, len(reversed_messages))

        # Slice the list for pagination
        messages = reversed_messages[start:end_index]

        ## Convert to json
        ## Add a tag indicating in-context or not
        # json_messages = [{**record.to_json(), "in_context": True} for record in messages]

    else:
        # need to access persistence manager for additional messages
        db_iterator = memgpt_agent.persistence_manager.recall_memory.storage.get_all_paginated(page_size=count, offset=start)

        # get a single page of messages
        # TODO: handle stop iteration
        page = next(db_iterator, [])

        # return messages in reverse chronological order
        messages = sorted(page, key=lambda x: x.created_at, reverse=True)
        assert all(isinstance(m, Message) for m in messages)

        ## Convert to json
        ## Add a tag indicating in-context or not
        # json_messages = [record.to_json() for record in messages]
        # in_context_message_ids = [str(m.id) for m in memgpt_agent._messages]
        # for d in json_messages:
        #    d["in_context"] = True if str(d["id"]) in in_context_message_ids else False

    if not return_message_object:
        messages = [msg for m in messages for msg in m.to_memgpt_message()]

    return messages


def get_agent_archival(self, user_id: str, agent_id: str, start: int, count: int) -> List[Passage]:
    """Paginated query of all messages in agent archival memory"""
    if self.ms.get_user(user_id=user_id) is None:
        raise ValueError(f"User user_id={user_id} does not exist")
    if self.ms.get_agent(agent_id=agent_id, user_id=user_id) is None:
        raise ValueError(f"Agent agent_id={agent_id} does not exist")

    # Get the agent object (loaded in memory)
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)

    # iterate over records
    db_iterator = memgpt_agent.persistence_manager.archival_memory.storage.get_all_paginated(page_size=count, offset=start)

    # get a single page of messages
    page = next(db_iterator, [])
    return page


def get_agent_archival_cursor(
    self,
    user_id: str,
    agent_id: str,
    after: Optional[str] = None,
    before: Optional[str] = None,
    limit: Optional[int] = 100,
    order_by: Optional[str] = "created_at",
    reverse: Optional[bool] = False,
) -> List[Passage]:
    if self.ms.get_user(user_id=user_id) is None:
        raise ValueError(f"User user_id={user_id} does not exist")
    if self.ms.get_agent(agent_id=agent_id, user_id=user_id) is None:
        raise ValueError(f"Agent agent_id={agent_id} does not exist")

    # Get the agent object (loaded in memory)
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)

    # iterate over recorde
    cursor, records = memgpt_agent.persistence_manager.archival_memory.storage.get_all_cursor(
        after=after, before=before, limit=limit, order_by=order_by, reverse=reverse
    )
    return records


def insert_archival_memory(self, user_id: str, agent_id: str, memory_contents: str) -> List[Passage]:
    if self.ms.get_user(user_id=user_id) is None:
        raise ValueError(f"User user_id={user_id} does not exist")
    if self.ms.get_agent(agent_id=agent_id, user_id=user_id) is None:
        raise ValueError(f"Agent agent_id={agent_id} does not exist")

    # Get the agent object (loaded in memory)
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)

    # Insert into archival memory
    passage_ids = memgpt_agent.persistence_manager.archival_memory.insert(memory_string=memory_contents, return_ids=True)

    # TODO: this is gross, fix
    return [memgpt_agent.persistence_manager.archival_memory.storage.get(id=passage_id) for passage_id in passage_ids]


def delete_archival_memory(self, user_id: str, agent_id: str, memory_id: str):
    if self.ms.get_user(user_id=user_id) is None:
        raise ValueError(f"User user_id={user_id} does not exist")
    if self.ms.get_agent(agent_id=agent_id, user_id=user_id) is None:
        raise ValueError(f"Agent agent_id={agent_id} does not exist")

    # TODO: should return a passage

    # Get the agent object (loaded in memory)
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)

    # Delete by ID
    # TODO check if it exists first, and throw error if not
    memgpt_agent.persistence_manager.archival_memory.storage.delete({"id": memory_id})

    # TODO: return archival memory


def get_agent_recall_cursor(
    self,
    user_id: str,
    agent_id: str,
    after: Optional[str] = None,
    before: Optional[str] = None,
    limit: Optional[int] = 100,
    order_by: Optional[str] = "created_at",
    order: Optional[str] = "asc",
    reverse: Optional[bool] = False,
    return_message_object: bool = True,
) -> Union[List[Message], List[MemGPTMessage]]:
    if self.ms.get_user(user_id=user_id) is None:
        raise ValueError(f"User user_id={user_id} does not exist")
    if self.ms.get_agent(agent_id=agent_id, user_id=user_id) is None:
        raise ValueError(f"Agent agent_id={agent_id} does not exist")

    # Get the agent object (loaded in memory)
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)

    # iterate over records
    cursor, records = memgpt_agent.persistence_manager.recall_memory.storage.get_all_cursor(
        after=after, before=before, limit=limit, order_by=order_by, reverse=reverse
    )

    assert all(isinstance(m, Message) for m in records)

    if not return_message_object:
        # If we're GETing messages in reverse, we need to reverse the inner list (generated by to_memgpt_message)
        if reverse:
            records = [msg for m in records for msg in m.to_memgpt_message()[::-1]]
        else:
            records = [msg for m in records for msg in m.to_memgpt_message()]

    return records


def get_agent_state(self, user_id: str, agent_id: Optional[str], agent_name: Optional[str] = None) -> Optional[AgentState]:
    """Return the config of an agent"""
    if self.ms.get_user(user_id=user_id) is None:
        raise ValueError(f"User user_id={user_id} does not exist")
    if agent_id:
        if self.ms.get_agent(agent_id=agent_id, user_id=user_id) is None:
            return None
    else:
        agent_state = self.ms.get_agent(agent_name=agent_name, user_id=user_id)
        if agent_state is None:
            raise ValueError(f"Agent agent_name={agent_name} does not exist")
        agent_id = agent_state.id

    # Get the agent object (loaded in memory)
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)
    assert isinstance(memgpt_agent.memory, Memory)
    assert isinstance(memgpt_agent.agent_state.memory, Memory)
    return memgpt_agent.agent_state.model_copy(deep=True)


def get_server_config(self, include_defaults: bool = False) -> dict:
    """Return the base config"""

    def clean_keys(config):
        config_copy = config.copy()
        for k, v in config.items():
            if k == "key" or "_key" in k:
                config_copy[k] = server_utils.shorten_key_middle(v, chars_each_side=5)
        return config_copy

    # TODO: do we need a seperate server config?
    base_config = vars(self.config)
    clean_base_config = clean_keys(base_config)

    clean_base_config_default_llm_config_dict = vars(clean_base_config["default_llm_config"])
    clean_base_config_default_embedding_config_dict = vars(clean_base_config["default_embedding_config"])

    clean_base_config["default_llm_config"] = clean_base_config_default_llm_config_dict
    clean_base_config["default_embedding_config"] = clean_base_config_default_embedding_config_dict
    response = {"config": clean_base_config}

    if include_defaults:
        default_config = vars(MemGPTConfig())
        clean_default_config = clean_keys(default_config)
        clean_default_config["default_llm_config"] = clean_base_config_default_llm_config_dict
        clean_default_config["default_embedding_config"] = clean_base_config_default_embedding_config_dict
        response["defaults"] = clean_default_config

    return response


def get_available_models(self) -> List[LLMConfig]:
    """Poll the LLM endpoint for a list of available models"""

    credentials = MemGPTCredentials().load()

    try:
        model_options = get_model_options(
            credentials=credentials,
            model_endpoint_type=self.config.default_llm_config.model_endpoint_type,
            model_endpoint=self.config.default_llm_config.model_endpoint,
        )
        return model_options

    except Exception as e:
        logger.exception(f"Failed to get list of available models from LLM endpoint:\n{str(e)}")
        raise


def update_agent_core_memory(self, user_id: str, agent_id: str, new_memory_contents: dict) -> Memory:
    """Update the agents core memory block, return the new state"""
    if self.ms.get_user(user_id=user_id) is None:
        raise ValueError(f"User user_id={user_id} does not exist")
    if self.ms.get_agent(agent_id=agent_id, user_id=user_id) is None:
        raise ValueError(f"Agent agent_id={agent_id} does not exist")

    # Get the agent object (loaded in memory)
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)

    # old_core_memory = self.get_agent_memory(agent_id=agent_id)

    modified = False
    for key, value in new_memory_contents.items():
        if memgpt_agent.memory.get_block(key) is None:
            # raise ValueError(f"Key {key} not found in agent memory {list(memgpt_agent.memory.list_block_names())}")
            raise ValueError(f"Key {key} not found in agent memory {str(memgpt_agent.memory.memory)}")
        if value is None:
            continue
        if memgpt_agent.memory.get_block(key) != value:
            memgpt_agent.memory.update_block_value(name=key, value=value)  # update agent memory
            modified = True

    # If we modified the memory contents, we need to rebuild the memory block inside the system message
    if modified:
        memgpt_agent.rebuild_memory()
        # save agent
        save_agent(memgpt_agent, self.ms)

    return self.ms.get_agent(agent_id=agent_id).memory


def rename_agent(self, user_id: str, agent_id: str, new_agent_name: str) -> AgentState:
    """Update the name of the agent in the database"""
    if self.ms.get_user(user_id=user_id) is None:
        raise ValueError(f"User user_id={user_id} does not exist")
    if self.ms.get_agent(agent_id=agent_id, user_id=user_id) is None:
        raise ValueError(f"Agent agent_id={agent_id} does not exist")

    # Get the agent object (loaded in memory)
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)

    current_name = memgpt_agent.agent_state.name
    if current_name == new_agent_name:
        raise ValueError(f"New name ({new_agent_name}) is the same as the current name")

    try:
        memgpt_agent.agent_state.name = new_agent_name
        self.ms.update_agent(agent=memgpt_agent.agent_state)
    except Exception as e:
        logger.exception(f"Failed to update agent name with:\n{str(e)}")
        raise ValueError(f"Failed to update agent name in database")

    assert isinstance(memgpt_agent.agent_state.id, str)
    return memgpt_agent.agent_state


def delete_user(self, user_id: str):
    # TODO: delete user
    pass


def delete_agent(self, user_id: str, agent_id: str):
    """Delete an agent in the database"""
    if self.ms.get_user(user_id=user_id) is None:
        raise ValueError(f"User user_id={user_id} does not exist")
    if self.ms.get_agent(agent_id=agent_id, user_id=user_id) is None:
        raise ValueError(f"Agent agent_id={agent_id} does not exist")

    # Verify that the agent exists and is owned by the user
    agent_state = self.ms.get_agent(agent_id=agent_id, user_id=user_id)
    if not agent_state:
        raise ValueError(f"Could not find agent_id={agent_id} under user_id={user_id}")
    if agent_state.user_id != user_id:
        raise ValueError(f"Could not authorize agent_id={agent_id} with user_id={user_id}")

    # First, if the agent is in the in-memory cache we should remove it
    # List of {'user_id': user_id, 'agent_id': agent_id, 'agent': agent_obj} dicts
    try:
        self.active_agents = [d for d in self.active_agents if str(d["agent_id"]) != str(agent_id)]
    except Exception as e:
        logger.exception(f"Failed to delete agent {agent_id} from cache via ID with:\n{str(e)}")
        raise ValueError(f"Failed to delete agent {agent_id} from cache")

    # Next, attempt to delete it from the actual database
    try:
        self.ms.delete_agent(agent_id=agent_id)
    except Exception as e:
        logger.exception(f"Failed to delete agent {agent_id} via ID with:\n{str(e)}")
        raise ValueError(f"Failed to delete agent {agent_id} in database")


def authenticate_user(self) -> str:
    # TODO: Implement actual authentication to enable multi user setup
    return str(MemGPTConfig.load().anon_clientid)


def api_key_to_user(self, api_key: str) -> str:
    """Decode an API key to a user"""
    user = self.ms.get_user_from_api_key(api_key=api_key)
    if user is None:
        raise HTTPException(status_code=403, detail="Invalid credentials")
    else:
        return user.id


def create_api_key(self, request: APIKeyCreate) -> APIKey:  # TODO: add other fields
    """Create a new API key for a user"""
    if request.name is None:
        request.name = f"API Key {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    token = self.ms.create_api_key(user_id=request.user_id, name=request.name)
    return token


def list_api_keys(self, user_id: str) -> List[APIKey]:
    """List all API keys for a user"""
    return self.ms.get_all_api_keys_for_user(user_id=user_id)


def delete_api_key(self, api_key: str) -> APIKey:
    api_key_obj = self.ms.get_api_key(api_key=api_key)
    if api_key_obj is None:
        raise ValueError("API key does not exist")
    self.ms.delete_api_key(api_key=api_key)
    return api_key_obj


def create_source(self, request: SourceCreate, user_id: str) -> Source:  # TODO: add other fields
    """Create a new data source"""
    source = Source(
        name=request.name,
        user_id=user_id,
        embedding_config=self.config.default_embedding_config,
    )
    self.ms.create_source(source)
    assert self.ms.get_source(source_name=request.name, user_id=user_id) is not None, f"Failed to create source {request.name}"
    return source


def update_source(self, request: SourceUpdate, user_id: str) -> Source:
    """Update an existing data source"""
    if not request.id:
        existing_source = self.ms.get_source(source_name=request.name, user_id=user_id)
    else:
        existing_source = self.ms.get_source(source_id=request.id)
    if not existing_source:
        raise ValueError("Source does not exist")

    # override updated fields
    if request.name:
        existing_source.name = request.name
    if request.metadata_:
        existing_source.metadata_ = request.metadata_
    if request.description:
        existing_source.description = request.description

    self.ms.update_source(existing_source)
    return existing_source


def delete_source(self, source_id: str, user_id: str):
    """Delete a data source"""
    source = self.ms.get_source(source_id=source_id, user_id=user_id)
    self.ms.delete_source(source_id)

    # delete data from passage store
    passage_store = StorageConnector.get_storage_connector(TableType.PASSAGES, self.config, user_id=user_id)
    passage_store.delete({"source_id": source_id})

    # TODO: delete data from agent passage stores (?)


def create_job(self, user_id: str) -> Job:
    """Create a new job"""
    job = Job(
        user_id=user_id,
        status=JobStatus.created,
    )
    self.ms.create_job(job)
    return job


def delete_job(self, job_id: str):
    """Delete a job"""
    self.ms.delete_job(job_id)


def get_job(self, job_id: str) -> Job:
    """Get a job"""
    return self.ms.get_job(job_id)


def list_jobs(self, user_id: str) -> List[Job]:
    """List all jobs for a user"""
    return self.ms.list_jobs(user_id=user_id)


def list_active_jobs(self, user_id: str) -> List[Job]:
    """List all active jobs for a user"""
    jobs = self.ms.list_jobs(user_id=user_id)
    return [job for job in jobs if job.status in [JobStatus.created, JobStatus.running]]


def load_file_to_source(self, source_id: str, file_path: str, job_id: str) -> Job:

    # update job
    job = self.ms.get_job(job_id)
    job.status = JobStatus.running
    self.ms.update_job(job)

    # try:
    from memgpt.data_sources.connectors import DirectoryConnector

    source = self.ms.get_source(source_id=source_id)
    connector = DirectoryConnector(input_files=[file_path])
    num_passages, num_documents = self.load_data(user_id=source.user_id, source_name=source.name, connector=connector)
    # except Exception as e:
    #    # job failed with error
    #    error = str(e)
    #    print(error)
    #    job.status = JobStatus.failed
    #    job.metadata_["error"] = error
    #    self.ms.update_job(job)
    #    # TODO: delete any associated passages/documents?

    #    # return failed job
    #    return job

    # update job status
    job.status = JobStatus.completed
    job.metadata_["num_passages"] = num_passages
    job.metadata_["num_documents"] = num_documents
    self.ms.update_job(job)

    return job


def load_data(
    self,
    user_id: str,
    connector: DataConnector,
    source_name: str,
) -> Tuple[int, int]:
    """Load data from a DataConnector into a source for a specified user_id"""
    # TODO: this should be implemented as a batch job or at least async, since it may take a long time

    # load data from a data source into the document store
    source = self.ms.get_source(source_name=source_name, user_id=user_id)
    if source is None:
        raise ValueError(f"Data source {source_name} does not exist for user {user_id}")

    # get the data connectors
    passage_store = StorageConnector.get_storage_connector(TableType.PASSAGES, self.config, user_id=user_id)
    # TODO: add document store support
    document_store = None  # StorageConnector.get_storage_connector(TableType.DOCUMENTS, self.config, user_id=user_id)

    # load data into the document store
    passage_count, document_count = load_data(connector, source, passage_store, document_store)
    return passage_count, document_count


def attach_source_to_agent(
    self,
    user_id: str,
    agent_id: str,
    # source_id: str,
    source_id: Optional[str] = None,
    source_name: Optional[str] = None,
) -> Source:
    # attach a data source to an agent
    data_source = self.ms.get_source(source_id=source_id, user_id=user_id, source_name=source_name)
    if data_source is None:
        raise ValueError(f"Data source id={source_id} name={source_name} does not exist for user_id {user_id}")

    # get connection to data source storage
    source_connector = StorageConnector.get_storage_connector(TableType.PASSAGES, self.config, user_id=user_id)

    # load agent
    agent = self._get_or_load_agent(agent_id=agent_id)

    # attach source to agent
    agent.attach_source(data_source.id, source_connector, self.ms)

    return data_source


def detach_source_from_agent(
    self,
    user_id: str,
    agent_id: str,
    # source_id: str,
    source_id: Optional[str] = None,
    source_name: Optional[str] = None,
) -> Source:
    # TODO: remove all passages coresponding to source from agent's archival memory
    raise NotImplementedError


def list_attached_sources(self, agent_id: str) -> List[Source]:
    # list all attached sources to an agent
    return self.ms.list_attached_sources(agent_id)


def list_data_source_passages(self, user_id: str, source_id: str) -> List[Passage]:
    warnings.warn("list_data_source_passages is not yet implemented, returning empty list.", category=UserWarning)
    return []


def list_data_source_documents(self, user_id: str, source_id: str) -> List[Document]:
    warnings.warn("list_data_source_documents is not yet implemented, returning empty list.", category=UserWarning)
    return []


def list_all_sources(self, user_id: str) -> List[Source]:
    """List all sources (w/ extra metadata) belonging to a user"""

    sources = self.ms.list_sources(user_id=user_id)

    # Add extra metadata to the sources
    sources_with_metadata = []
    for source in sources:

        # count number of passages
        passage_conn = StorageConnector.get_storage_connector(TableType.PASSAGES, self.config, user_id=user_id)
        num_passages = passage_conn.size({"source_id": source.id})

        # TODO: add when documents table implemented
        ## count number of documents
        # document_conn = StorageConnector.get_storage_connector(TableType.DOCUMENTS, self.config, user_id=user_id)
        # num_documents = document_conn.size({"data_source": source.name})
        num_documents = 0

        agent_ids = self.ms.list_attached_agents(source_id=source.id)
        # add the agent name information
        attached_agents = [
            {
                "id": str(a_id),
                "name": self.ms.get_agent(user_id=user_id, agent_id=a_id).name,
            }
            for a_id in agent_ids
        ]

        # Overwrite metadata field, should be empty anyways
        source.metadata_ = dict(
            num_documents=num_documents,
            num_passages=num_passages,
            attached_agents=attached_agents,
        )

        sources_with_metadata.append(source)

    return sources_with_metadata


# def get_tool(self, tool_id: str) -> Optional[Tool]:
#    """Get tool by ID."""
#    return self.ms.get_tool(tool_id=tool_id)


def get_tool_id(self, name: str, user_id: str) -> Optional[str]:
    """Get tool ID from name and user_id."""
    tool = self.ms.get_tool(tool_name=name, user_id=user_id)
    if not tool or tool.id is None:
        return None
    return tool.id


def update_tool(
    self,
    request: ToolUpdate,
) -> Tool:
    """Update an existing tool"""
    existing_tool = self.ms.get_tool(tool_id=request.id)
    if not existing_tool:
        raise ValueError(f"Tool does not exist")

    # override updated fields
    if request.source_code:
        existing_tool.source_code = request.source_code
    if request.source_type:
        existing_tool.source_type = request.source_type
    if request.tags:
        existing_tool.tags = request.tags
    if request.json_schema:
        existing_tool.json_schema = request.json_schema
    if request.name:
        existing_tool.name = request.name

    self.ms.update_tool(existing_tool)
    return self.ms.get_tool(tool_id=request.id)


def create_tool(self, request: ToolCreate, user_id: Optional[str] = None, update: bool = True) -> Tool:  # TODO: add other fields
    """Create a new tool"""

    # NOTE: deprecated code that existed when we were trying to pretend that `self` was the memory object
    # if request.tags and "memory" in request.tags:
    #    # special modifications to memory functions
    #    # self.memory -> self.memory.memory, since Agent.memory.memory needs to be modified (not BaseMemory.memory)
    #    request.source_code = request.source_code.replace("self.memory", "self.memory.memory")

    if not request.json_schema:
        # auto-generate openai schema
        try:
            env = {}
            env.update(globals())
            exec(request.source_code, env)

            # get available functions
            functions = [f for f in env if callable(env[f])]

        except Exception as e:
            logger.error(f"Failed to execute source code: {e}")

        # TODO: not sure if this always works
        func = env[functions[-1]]
        json_schema = generate_schema(func, request.name)
    else:
        # provided by client
        json_schema = request.json_schema

    if not request.name:
        # use name from JSON schema
        request.name = json_schema["name"]
        assert request.name, f"Tool name must be provided in json_schema {json_schema}. This should never happen."

    # check if already exists:
    existing_tool = self.ms.get_tool(tool_name=request.name, user_id=user_id)
    if existing_tool:
        if update:
            updated_tool = self.update_tool(ToolUpdate(id=existing_tool.id, **vars(request)))
            assert updated_tool is not None, f"Failed to update tool {request.name}"
            return updated_tool
        else:
            raise ValueError(f"Tool {request.name} already exists and update=False")

    tool = Tool(
        name=request.name,
        source_code=request.source_code,
        source_type=request.source_type,
        tags=request.tags,
        json_schema=json_schema,
        user_id=user_id,
    )
    self.ms.create_tool(tool)
    created_tool = self.ms.get_tool(tool_name=request.name, user_id=user_id)
    return created_tool


def delete_tool(self, tool_id: str):
    """Delete a tool"""
    self.ms.delete_tool(tool_id)


def list_tools(self, user_id: str) -> List[Tool]:
    """List tools available to user_id"""
    tools = self.ms.list_tools(user_id)
    return tools


def add_default_tools(self, module_name="base", user_id: Optional[str] = None):
    """Add default tools in {module_name}.py"""
    full_module_name = f"memgpt.functions.function_sets.{module_name}"
    try:
        module = importlib.import_module(full_module_name)
    except Exception as e:
        # Handle other general exceptions
        raise e

    try:
        # Load the function set
        functions_to_schema = load_function_set(module)
    except ValueError as e:
        err = f"Error loading function set '{module_name}': {e}"

    # create tool in db
    for name, schema in functions_to_schema.items():
        # print([str(inspect.getsource(line)) for line in schema["imports"]])
        source_code = inspect.getsource(schema["python_function"])
        tags = [module_name]
        if module_name == "base":
            tags.append("memgpt-base")

        # create to tool
        self.create_tool(
            ToolCreate(
                name=name,
                tags=tags,
                source_type="python",
                module=schema["module"],
                source_code=source_code,
                json_schema=schema["json_schema"],
                user_id=user_id,
            ),
            update=True,
        )


def add_default_blocks(self, user_id: str):
    from memgpt.utils import list_human_files, list_persona_files

    assert user_id is not None, "User ID must be provided"

    for persona_file in list_persona_files():
        text = open(persona_file, "r", encoding="utf-8").read()
        name = os.path.basename(persona_file).replace(".txt", "")
        self.create_block(CreatePersona(user_id=user_id, name=name, value=text, template=True), user_id=user_id, update=True)

    for human_file in list_human_files():
        text = open(human_file, "r", encoding="utf-8").read()
        name = os.path.basename(human_file).replace(".txt", "")
        self.create_block(CreateHuman(user_id=user_id, name=name, value=text, template=True), user_id=user_id, update=True)


def get_agent_message(self, agent_id: str, message_id: str) -> Optional[Message]:
    """Get a single message from the agent's memory"""
    # Get the agent object (loaded in memory)
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)
    message = memgpt_agent.persistence_manager.recall_memory.storage.get(id=message_id)
    return message


def update_agent_message(self, agent_id: str, request: UpdateMessage) -> Message:
    """Update the details of a message associated with an agent"""

    # Get the current message
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)
    return memgpt_agent.update_message(request=request)

    # TODO decide whether this should be done in the server.py or agent.py
    # Reason to put it in agent.py:
    # - we use the agent object's persistence_manager to update the message
    # - it makes it easy to do things like `retry`, `rethink`, etc.
    # Reason to put it in server.py:
    # - fundamentally, we should be able to edit a message (without agent id)
    #   in the server by directly accessing the DB / message store
    """
    message = memgpt_agent.persistence_manager.recall_memory.storage.get(id=request.id)
    if message is None:
        raise ValueError(f"Message with id {request.id} not found")

    # Override fields
    # NOTE: we try to do some sanity checking here (see asserts), but it's not foolproof
    if request.role:
        message.role = request.role
    if request.text:
        message.text = request.text
    if request.name:
        message.name = request.name
    if request.tool_calls:
        assert message.role == MessageRole.assistant, "Tool calls can only be added to assistant messages"
        message.tool_calls = request.tool_calls
    if request.tool_call_id:
        assert message.role == MessageRole.tool, "tool_call_id can only be added to tool messages"
        message.tool_call_id = request.tool_call_id

    # Save the updated message
    memgpt_agent.persistence_manager.recall_memory.storage.update(record=message)

    # Return the updated message
    updated_message = memgpt_agent.persistence_manager.recall_memory.storage.get(id=message.id)
    if updated_message is None:
        raise ValueError(f"Error persisting message - message with id {request.id} not found")
    return updated_message
    """


def rewrite_agent_message(self, agent_id: str, new_text: str) -> Message:

    # Get the current message
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)
    return memgpt_agent.rewrite_message(new_text=new_text)


def rethink_agent_message(self, agent_id: str, new_thought: str) -> Message:

    # Get the current message
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)
    return memgpt_agent.rethink_message(new_thought=new_thought)


def retry_agent_message(self, agent_id: str) -> List[Message]:

    # Get the current message
    memgpt_agent = self._get_or_load_agent(agent_id=agent_id)
    return memgpt_agent.retry_message()


# TODO(ethan) wire back to real method in future ORM PR
def get_current_user(self) -> User:
    """Returns the currently authed user.

    Since server is the core gateway this needs to pass through server as the
    first touchpoint.
    """
    # NOTE: same code as local client to get the default user
    config = MemGPTConfig.load()
    user_id = config.anon_clientid
    user = self.get_user(user_id)

    if not user:
        user = self.create_user(UserCreate())

        # # update config
        config.anon_clientid = str(user.id)
        config.save()

    return user


def list_models(self) -> List[LLMConfig]:
    """List available models"""

    # TODO support multiple models
    llm_config = self.server_llm_config
    return [llm_config]


def list_embedding_models(self) -> List[EmbeddingConfig]:
    """List available embedding models"""

    # TODO support multiple models
    embedding_config = self.server_embedding_config
    return [embedding_config]