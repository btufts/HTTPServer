# You need to implement the "get" and "head" functions.
import os


class FileReader:
    def __init__(self):
        pass

    def get(self, filepath, cookies):
        """
        Returns a binary string of the file contents, or None.

        """

        if os.path.isfile(filepath):
            with open(filepath, "rb") as file:
                content = file.read()
        else:
            content = "<html><body><h1>" + \
                str(filepath)+"</h1></body></html>"
            content = content.encode()

        return content

    def head(self, filepath, cookies):
        """
        Returns the size to be returned, or None.
        """
        try:
            file_size = os.path.getsize(filepath)
        except:
            file_size = None

        if os.path.isdir(filepath):
            file_size = None

        return file_size
