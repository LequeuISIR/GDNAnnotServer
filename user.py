import os 
from pathlib import Path
import pickle
import json
from const import NUM_ANNOTATIONS_BEFORE_SHARED
import time
from datetime import datetime
from filelock import FileLock
import tempfile

class User :
    def __init__(self, token):
        """
        Token will be provided by the company
        """

        if self.token_already_exist(token) :
            # this token is already used by another annotator
            return ValueError
        
        # else create the user
        self.token = token
        self.create_user()

    @classmethod
    def token_already_exist(self, token) :
        return Path(f"./annotators/{token}").is_dir()
    

    def __str__(self):
        return (f"=== USER {self.token} ===\n \
                CURRENT ANNOTATION {self.current_annotation}\n \
                DONE ANNOTATIONS {self.done_annotations}")

        pass
    def create_user(self) :
        os.makedirs(f"./annotators/{self.token}/")
        open(f"./annotators/{self.token}/annotations.jsonl", 'a').close()
        open(f"./annotators/{self.token}/reports.jsonl", 'a').close()

        # self.current_batch = None # current batch index
        # self.current_index = 0 # current index in the batch
        self.current_annotation = None
        self.done_annotations = []
        self.num_shared_batches = 0
        self.start_annotation_time = None
        self.last_used_llm = None
        self.save_user()


    def num_annotated_batch(self) :
        return len(self.done_annotations)
    
    def save_user(self) :
        user_file = f"./annotators/{self.token}/user.pkl"
        lock = FileLock(user_file + ".lock")
        with lock:
            # write to temp file first
            with tempfile.NamedTemporaryFile('wb', delete=False, dir=os.path.dirname(user_file)) as tmp:
                pickle.dump(self, tmp)
                temp_name = tmp.name
            os.replace(temp_name, user_file)  # atomic replace


    @classmethod
    def load_user(cls, token) :
        user_file = f"./annotators/{token}/user.pkl"
        lock = FileLock(user_file + ".lock")
        with lock:
            try:
                with open(user_file, "rb") as f:
                    return pickle.load(f)
            except Exception:
                raise ValueError
    
    def can_be_second_annotator(self) :
        return self.num_annotated_batch() > NUM_ANNOTATIONS_BEFORE_SHARED

    def new_opinion(self, opinion) :
        self.current_annotation = opinion["opinionId"]
        print(f"new annotation for user {self.token}: {self.current_annotation}")
        self.start_annotation_time = time.time()
        self.save_user()


    def save_last_llm(self, model) :
        self.last_used_llm = model
        self.save_user()

    def report_data(self, data) :
        file_path = f"./annotators/{self.token}/reports.jsonl"
        self.write_jsonl(data, file_path)
        self.done_annotations.append(self.current_annotation)
        self.current_annotation = None
        self.save_user()            

    def save_annotation(self, data) :
        file_path = f"./annotators/{self.token}/annotations.jsonl"
        data["time"] = time.time() - self.start_annotation_time
        data["date"] = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

        self.write_jsonl(data, file_path)
        self.done_annotations.append(self.current_annotation)
        self.current_annotation = None
        self.save_user()
       
    
    def write_jsonl(self, data, file_path) :
        lock = FileLock(file_path + ".lock")
        with lock:
            # read old content (if any)
            lines = []
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    lines = f.readlines()

            # append new line
            lines.append(json.dumps(data) + "\n")

            # write atomically
            with tempfile.NamedTemporaryFile('w', delete=False, dir=os.path.dirname(file_path)) as tmp:
                tmp.writelines(lines)
                temp_name = tmp.name
            os.replace(temp_name, file_path)
            


            
        
if __name__ == "__main__" :
    user = User("huhu")

    print("current batch", user.current_batch)
    print("current index", user.current_index)
    for i in range(50) :
        line = user.get_next_line()
        print(user.current_batch, user.current_index, line, user.done_batches)
        user.save_data(line)
        user.iterate_line()
        user.save_user()
        time.sleep(1)




