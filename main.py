import os
import re
import json
import subprocess
from git import Repo
from colorama import Fore, Style, init
from datetime import datetime
import shutil
# Initialize Colorama
init(autoreset=True)

def get_input(prompt, default=None):
    """ Helper function to get input from the user. """
    user_input = input(prompt)
    return user_input.strip() if user_input else default

def load_or_initialize_config():
    """ Load or create a configuration file as per user's choice. """
    config_file = get_input("Enter the path to a configuration file or press enter to use default: ")
    if not config_file:
        config_file = 'default_config.json'  # Default file
    try:
        with open(config_file, 'r') as file:
            config = json.load(file)
    except FileNotFoundError:
        print("Configuration file not found. Initializing with default settings.")
        config = {
            "regex_patterns": [],
            "excluded_extensions": [],
            "excluded_paths": [],
            "excluded_strings": []
        }
        save_config(config, config_file)
    return config, config_file
def edit_regex_patterns(config):
    """ Function to edit list of regex patterns and associated messages. """
    for index, item in enumerate(config['regex_patterns']):
        print(f"{index+1}. Pattern: {item['pattern']}, Message: {item['message']}")
    choice = get_input("Do you want to add or remove a pattern? (add/remove): ")
    if choice.lower() == 'add':
        pattern = get_input("Enter new regex pattern: ")
        message = get_input("Enter message for this pattern: ")
        config['regex_patterns'].append({"pattern": pattern, "message": message})
    elif choice.lower() == 'remove':
        index = int(get_input("Enter the number of the pattern to remove: ")) - 1
        if 0 <= index < len(config['regex_patterns']):
            del config['regex_patterns'][index]
def backup_repository(repo_path):
    """ Back up the repository to a subfolder in the current script's directory. """
    # Get the current script's directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backup_dir = os.path.join(current_dir, 'backups')

    # Create a backup directory if it does not exist
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # Define the backup repository path with a timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    backup_repo_path = os.path.join(backup_dir, f'backup_{timestamp}')

    # Copy the entire repository directory
    shutil.copytree(repo_path, backup_repo_path)

    print(f"Repository backed up successfully to {backup_repo_path}")
def save_config(config, config_file):
    """ Save the configuration to a file. """
    with open(config_file, 'w') as file:
        json.dump(config, file, indent=4)
    print(f"Configuration saved to {config_file}")
def edit_list(config, key):
    """ Edit list items in the configuration. """
    print(f"Current {key}: {', '.join(config[key])}")
    action = get_input(f"Do you want to add or remove items from {key}? (add/remove): ")
    if action.lower() == 'add':
        new_item = get_input("Enter item to add: ")
        config[key].append(new_item)
    elif action.lower() == 'remove':
        rem_item = get_input("Enter item to remove: ")
        if rem_item in config[key]:
            config[key].remove(rem_item)
    print(f"Updated {key}: {', '.join(config[key])}")
def remove_commits(repo_path, commits_to_remove):
    """ Remove specific commits from the history. """
    repo = Repo(repo_path)
    repo.git.rebase('HEAD', interactive=True, autosquash=True, keep_empty=True, strategy_option='remove_commits')

def main():
    config, config_file = load_or_initialize_config()

    repo_path = get_input("Enter the path of the repository (e.g., '~/my-repo'): ")
    branch_name = get_input("Enter the branch name to analyze (e.g., 'main'): ")
    repo = Repo(repo_path)
        # Backup the repository
    #backup_repository(repo_path)

    while True:
        print("\nMenu:")
        print("1. Edit regex patterns and messages")
        print("2. Edit excluded file extensions")
        print("3. Edit excluded strings")
        print("4. Edit excluded paths")
        print("5. Launch the scan")
       # print("6. Remove commits")
        print("7. Exit and save configuration")
        choice = get_input("Enter your choice: ")

        if choice == '1':
            edit_regex_patterns(config)
        elif choice == '2':
            edit_list(config, 'excluded_extensions')
        elif choice == '3':
            edit_list(config, 'excluded_strings')
        elif choice == '4':
            edit_list(config, 'excluded_paths')
        elif choice == '5':
            scan_results = launch_scan(repo, branch_name, config)
        elif choice == '6':
            if 'scan_results' in locals():
                remove_commits(repo_path, scan_results)
            else:
                print("No scan results available. Please run a scan first.")
        elif choice == '7':
            save_config(config, config_file)
            print("Exiting...")
            break
        else:
            print("Invalid choice, please try again.")

import re

def launch_scan(repo, branch_name, config):
    """ Launch the scanning process using the loaded configuration. """
    excluded_extensions = set(config['excluded_extensions'])
    excluded_paths = config['excluded_paths']
    excluded_strings = config['excluded_strings']
    commit_ids = []

    for commit in repo.iter_commits(branch_name):
        tree = commit.tree
        for file in commit.stats.files.keys():
            if any(file.endswith(ext) for ext in excluded_extensions) or any(file_path in file for file_path in excluded_paths):
                continue  # Skip files based on extensions and paths
            
            try:
                # Check if the file exists in the tree before accessing its blob
                if file in tree:
                    blob = tree[file]
                    content = blob.data_stream.read().decode('utf-8', errors='ignore')
                    for pattern_info in config['regex_patterns']:
                        regex = re.compile(pattern_info['pattern'])
                        matches = regex.findall(content)
                        # Filter out matches that are in the excluded_strings
                        filtered_matches = [match for match in matches if match not in excluded_strings]
                        if filtered_matches:
                            commit_ids.append(commit.hexsha)
                            print(Fore.GREEN + f'Commit {commit.hexsha}')
                            print(Fore.CYAN + f'File {file}:')
                            print(Fore.YELLOW + f'{pattern_info["message"]} {filtered_matches}\n')
              #  else:
                    # Log or handle cases where the file does not exist in the commit's tree
                  #  print(Fore.YELLOW + f"File {file} not found in commit {commit.hexsha}. It may have been renamed or deleted.")
            except Exception as e:
                print(Fore.RED + f'Error reading file {file}: {e}')

    return commit_ids



if __name__ == "__main__":
    main()
