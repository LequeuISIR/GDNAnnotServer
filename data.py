from const import DATA_FILE, ANNOTATORS_DIR, ALL_ANNOTATIONS_OUTPUT_FILE, ALL_REPORTS_OUTPUT_FILE
import pandas as pd
import os
from filelock import FileLock
import json
from user import User

class GDNData :
    def __init__(self):
        self.data = self.load_data()

    def load_data(self) :
        print("setting up dataframe...")
        data = pd.read_json(DATA_FILE, lines = True)
        data["num_finished_annotations"] = 0
        data["is_being_annotated"] = False
        data["llm_1"] = ""
        data["llm_2"] = ""

        print("collection already existing annotations...")
        collect_all_annotations()

        # get all already-done annotations
        print("reading existing annotations...")
        try :
            with open(ALL_ANNOTATIONS_OUTPUT_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        line = json.loads(line)
                    except json.JSONDecodeError:
                        print(f"Skipping invalid JSON in output file")
                        continue
                    data.loc[data["opinionId"] == line["opinion"]["opinionId"], "num_finished_annotations"] += 1
                    if data[data["opinionId"] == line["opinion"]["opinionId"]].iloc[0]["llm_1"] == "" :
                        data.loc[data["opinionId"] == line["opinion"]["opinionId"], "llm_1"] = "a"
                    else : 
                        data.loc[data["opinionId"] == line["opinion"]["opinionId"], "llm_2"]  = "a"
    
        except FileNotFoundError :
            print(f"no {ALL_ANNOTATIONS_OUTPUT_FILE} file found")
            pass
        
        # get all reported opinions
        print("reading existing reports...")
        try :
            with open(ALL_REPORTS_OUTPUT_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        line = json.loads(line)
                    except json.JSONDecodeError:
                        print(f"Skipping invalid JSON in output file")
                        continue
                    
                    data.loc[data["opinionId"] == line["opinion"]["opinionId"], "num_finished_annotations"] = -1
    
        except FileNotFoundError :
            print(f"no {ALL_REPORTS_OUTPUT_FILE} file found")
            pass

        return data

    def next_data(self, user: User) :
        print("CALING NEXT DATA")
        

        if user.can_be_second_annotator() :
            data = self.data[self.data["num_finished_annotations"] == 1]
            if not data.empty :
                i = 0
                while i < len(data) :
                    if (not data.iloc[i]["is_being_annotated"]) and (not (data.iloc[i]["opinionId"] in user.done_annotations)): 
                        line = data.iloc[i][["opinionId", "text", "authorName", "len"]]
                        line = line.to_dict()
                        self.data.loc[self.data["opinionId"] == line["opinionId"], "is_being_annotated"] = True

                        return line
                    i += 1
            
        # either the user cant be second annotator or there is not opinion to be annotated a second time
        i = 0
        data = self.data[self.data["num_finished_annotations"] == 0]
        while i < len(data) :
            if (not data.iloc[i]["is_being_annotated"]) and (not (data.iloc[i]["opinionId"] in user.done_annotations)):  
                line = data.iloc[i][["opinionId", "text", "authorName", "len"]]
                line = line.to_dict()
                self.data.loc[self.data["opinionId"] == line["opinionId"], "is_being_annotated"] = True
                return line 
            i += 1
            
        
        raise OverflowError("No more opinions to annotate")
    

    def cancel_opinion_annotation(self, opinionId) :
        self.data.loc[self.data["opinionId"] == opinionId, "is_being_annotated"] = False

    def set_opinion_annotation(self, opinionId) :
        self.data.loc[self.data["opinionId"] == opinionId, "is_being_annotated"] = True

    def add_finished_annotation(self, opinion) :
        self.data.loc[self.data["opinionId"] == opinion["opinion"]["opinionId"], "is_being_annotated"] = False
        self.data.loc[self.data["opinionId"] == opinion["opinion"]["opinionId"], "num_finished_annotations"] += 1

        if self.data[self.data["opinionId"] == opinion["opinion"]["opinionId"]].iloc[0]["llm_1"] == "" :
            self.data.loc[self.data["opinionId"] == opinion["opinion"]["opinionId"], "llm_1"] = opinion["llm"]
        else : 
            self.data.loc[self.data["opinionId"] == opinion["opinion"]["opinionId"], "llm_2"] = opinion["llm"]

    def add_reported_annotation(self, opinion) :
        self.data.loc[self.data["opinionId"] == opinion["opinion"]["opinionId"], "is_being_annotated"] = False
        self.data.loc[self.data["opinionId"] == opinion["opinion"]["opinionId"], "num_finished_annotations"] = -1


    def get_data_from_id(self, opinionId) :
        line = self.data[self.data["opinionId"] == opinionId].iloc[0][["opinionId", "text", "authorName", "len"]]
        line = line.to_dict()
        self.data.loc[self.data["opinionId"] == line["opinionId"], "is_being_annotated"] = True
        return line
    
    def get_used_llm(self, opinionId) :
        line = self.data[self.data["opinionId"] == opinionId].iloc[0]
        used_llms = []
        if line["llm_1"] :
            used_llms.append(line["llm_1"])
        if line["llm_2"] :
            used_llms.append(line["llm_2"])
        return used_llms


            




def collect_all_annotations():
    with open(ALL_ANNOTATIONS_OUTPUT_FILE, "w") as out_f:
        # iterate through each annotator directory
        for annotator in os.listdir(ANNOTATORS_DIR):
            if os.path.isdir(ANNOTATORS_DIR / annotator) :
                annotator_dir = os.path.join(ANNOTATORS_DIR, annotator)
                annotations_file = os.path.join(annotator_dir, "annotations.jsonl")

                if not os.path.isfile(annotations_file):
                    continue  # skip if the file doesn’t exist

                lock = FileLock(annotations_file + ".lock")
                with lock:
                    with open(annotations_file, "r") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                data["annotator"] = annotator  # add annotator ID
                                out_f.write(json.dumps(data) + "\n")
                            except json.JSONDecodeError:
                                print(f"Skipping invalid JSON in {annotations_file}")


    with open(ALL_REPORTS_OUTPUT_FILE, "w") as out_f:
        # iterate through each annotator directory
        for annotator in os.listdir(ANNOTATORS_DIR):
            if os.path.isdir(ANNOTATORS_DIR / annotator) :
                annotator_dir = os.path.join(ANNOTATORS_DIR, annotator)
                reports_file = os.path.join(annotator_dir, "reports.jsonl")

                if not os.path.isfile(reports_file):
                    continue  # skip if the file doesn’t exist

                lock = FileLock(reports_file + ".lock")
                with lock:
                    with open(reports_file, "r") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                data["annotator"] = annotator  # add annotator ID
                                out_f.write(json.dumps(data) + "\n")
                            except json.JSONDecodeError:
                                print(f"Skipping invalid JSON in {reports_file}")




if __name__ == "__main__" :
    collect_all_annotations()
