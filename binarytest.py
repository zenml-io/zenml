from zenml.client import Client
import os
import shutil

# delete the files located inside /Users/strickvl/Desktop/test/ directory
# folder = "/Users/strickvl/Desktop/test/"
# for filename in os.listdir(folder):
#     file_path = os.path.join(folder, filename)
#     try:
#         if os.path.isfile(file_path) or os.path.islink(file_path):
#             os.unlink(file_path)
#         elif os.path.isdir(file_path):
#             shutil.rmtree(file_path)
#     except Exception as e:
#         print(f"Failed to delete {file_path}. Reason: {e}")

c = Client()

av = c.get_artifact_version("725f86df-25ce-42c7-9342-2e46fbd918c6")

av.download_files(path="/Users/strickvl/Desktop/test/binary.zip")
