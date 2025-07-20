from uploader import LawCodeUploader


class LawCodeUploaderChain:
    def __init__(self, directory: str = "./codes"):
        self.directory = directory
    
    def explore(self):
        import os
        
        if not os.path.exists(self.directory):
            raise FileNotFoundError(f"The directory {self.directory} does not exist.")
        
        dirs = os.listdir(self.directory)
        if not dirs:
            print("No files found in the directory.")
            return
        
        print("Files in the directory:")
        for dir in dirs:
            if not os.path.isdir(os.path.join(self.directory, dir)):
                print(f"- {dir} is not directory, skipping.")
            print(f"- discovered... {dir} Starting law upload process.")
            uploader = LawCodeUploader(dir)
            uploader.run()