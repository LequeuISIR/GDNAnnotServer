import argparse
import os
import pickle
from user import User

from data import collect_all_annotations
from const import ANNOTATORS_DIR, EXAMPLES



def reload_users() :
    for annotator in os.listdir(ANNOTATORS_DIR):
            if os.path.isdir(ANNOTATORS_DIR / annotator) :
                print(annotator)
                user: User = User.load_user(annotator)
                new_user = User(user.token, override_already_existing=True)
                new_user.passed_tutorials = {key: True for key, _ in EXAMPLES.items()}
                new_user.done_annotations = user.done_annotations
                new_user.current_annotation = user.current_annotation
                new_user.last_used_llm = user.last_used_llm
                new_user.start_annotation_time = user.start_annotation_time
                new_user.save_user()

    

if __name__ == "__main__" :
    # Create the parser
    parser = argparse.ArgumentParser(description="Example parser with custom tags")

    # Define the --save-all flag (boolean switch)
    parser.add_argument(
        '--save-all',
        action='store_true',  # This makes it a flag (True if present)
        help='Save all data when this flag is used.'
    )

    # Define the --reload-user flag (boolean switch)
    parser.add_argument(
        '--reload-users',
        action='store_true',  # This makes it a flag (True if present)
        help='Reload users class to update it.'
    )

    # Parse the command-line arguments
    args = parser.parse_args()

    if args.save_all :
        collect_all_annotations()
    
    if args.reload_users :
         reload_users()
