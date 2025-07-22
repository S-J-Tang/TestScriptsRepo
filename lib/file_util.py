import fnmatch
import os
import shutil
def retrieve_latest_file(search_dir, pattern):# -> tuple[int, str, str]:

    file_list = fnmatch.filter(os.listdir(search_dir), pattern)

    if len(file_list) == 0:
        msg = f"Error: no FW package with pattern {pattern} in {search_dir}. Please check and try again."
        return 1, "", msg
    if len(file_list) > 1:
        file_list.sort(key=lambda s: os.path.getctime(os.path.join(search_dir, s)))
        file_list.reverse()
        msg = f"Warning: found more than one FW file with pattern {pattern}, using the lastest one:{file_list[0]}."
        return 0, os.path.join(search_dir, file_list[0]), msg

    msg = f"Found {file_list[0]}"
    return 0, os.path.join(search_dir, file_list[0]), msg

def backup_file(file_path, backup_dir):# -> tuple[int, str]:
    if not os.path.isfile(file_path):
        return 1, f"{file_path} is not a file"
    file_name = file_path.split("/")[-1]
    shutil.copy(file_path, backup_dir)
    if not os.path.isfile(f"{backup_dir}/{file_name}"):
        return 1, f"Fail to backup {file_name} to {backup_dir}"
    return 0, f"Backup {file_name} to {backup_dir} successfully"