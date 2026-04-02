class MemoryStore:

    def __init__(self):
        self.data = {}

    def add_message(self, user_id, message):

        if user_id not in self.data:
            self.data[user_id] = []

        self.data[user_id].append(message)

    def get_history(self, user_id):
        return self.data.get(user_id, [])

    def count(self, user_id):
        return len(self.get_history(user_id))


memory_store = MemoryStore()