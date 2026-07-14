from langgraph.checkpoint.base import BaseCheckpointSaver

from backend.adapters.memory.langgraph_memory import LangGraphMemory


class LangGraphCheckpointer(BaseCheckpointSaver):
    def __init__(self, memory: LangGraphMemory):
        super().__init__()
        self.memory = memory

    def get_tuple(self, config):
        thread_id = config["configurable"]["thread_id"]
        state = self.memory.get_state(thread_id)
        if not state:
            return None
        return (config, state, None)

    def put(self, config, checkpoint, metadata=None):
        thread_id = config["configurable"]["thread_id"]
        self.memory.update_state(thread_id, checkpoint)
        return config

    def put_writes(self, config, writes, task_id=None):
        pass
