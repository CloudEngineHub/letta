from memgpt.constants import BASE_TOOLS, DEFAULT_ORG_ID
from memgpt.schemas.agent import CreateAgent
from memgpt.schemas.memory import ChatMemory
from memgpt.server.stateless_server import Server, get_db, init_db

## NOTE: probably makes sense to start with just fixing MS, and leaving agent_store for later (too many changes)
# so basically, dont touch the agent for now

# def test_persistence_manager():
#
#    session = next(get_db())
#
#    conn = SQLLiteStorageConnector(table_type=TableType.ARCHIVAL_MEMORY, config=MemGPTConfig(), user_id="test_user")


def test_create_agent():
    session = next(get_db())

    # initialize database
    init_db(session)

    # create an agent
    server = Server()
    memory = ChatMemory(human="I am Sarah", persona="I am a bot")
    agent = server.create_agent(session, CreateAgent(name="test_agent", tools=BASE_TOOLS, memory=memory), org_id=DEFAULT_ORG_ID)
    print(agent)


test_create_agent()
