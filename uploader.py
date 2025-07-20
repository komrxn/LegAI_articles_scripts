import json
import os

from interfaces.metadata import Metadata

from requests import Session
import mimetypes

from rich.console import Console


console = Console()


class LawCodeUploader:
    def __init__(self, law_code: str, checkpoints: str = ".saved"):
        self.law_code = law_code
        self.path = os.path.abspath(os.path.join("codes", os.path.normpath(law_code)))
        self.metadata_path = os.path.join(self.path, "metadata.json")
        self.metadata = self.load_metadata()
        self.checkpoints_path = os.path.abspath(os.path.normpath(checkpoints))

        self.last_checkpoint: tuple[int, Metadata] | None = None

        self.session = Session()
    
    def load_metadata(self) -> list[Metadata]:
        """
        Load metadata from the metadata.json file.
        """
        if not os.path.exists(self.metadata_path):
            raise FileNotFoundError(f"Metadata file not found: {self.metadata_path}")
        
        metadata = json.load(open(self.metadata_path, "r"))
        
        return [Metadata.model_safe_validate(m) for m in metadata]
    
    def upload(self, metadata: Metadata):
        """
        Upload the law code to AgentHub.
        """
        file_path = os.path.join(self.path, metadata.file_path)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, "rb") as article_file:
            # Determine the content type of the file
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                raise ValueError(f"Unable to determine content type for file: {file_path}")
            
            # Upload the file to AgentHub
            response = self.session.post(
                "https://dev-api.ascender-ai.com/api/agents/1/files?bucket=rag-documents",
                files={"attachment": (os.path.basename(file_path), article_file, content_type)},
            )
            
            print(response)

            if response.status_code != 200:
                raise Exception(f"Failed to upload file: {response.text}")
        
        # Return the response
        return response
    
    def ingest(self, file_id: int, metadata: Metadata):
        """
        Ingest the law code into the database.
        """
        # Here you would implement the logic to ingest the law code into the database
        # For example, you could use an ORM or a direct SQL query to insert the data
        # into the database.
        print(metadata)
        response = self.session.post(
            "https://dev-api.ascender-ai.com/api/rag/documents/1/basic/legai",
            json={
                "file_ids": [file_id],
                "metadata": metadata.model_dump(mode="json", exclude={"article_title_number",}),
            },
            stream=True
        )
        
        print(response)
        if response.status_code != 200:
            raise Exception(f"Failed to ingest file: {response.text}")
        
        return response

    def save_checkpoint(self, index: int, metadata: Metadata):
        """
        Save a checkpoint of the current state.
        """
        checkpoint_path = os.path.join(self.checkpoints_path, self.law_code, f"{index}.json")
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
        
        with open(checkpoint_path, "w") as checkpoint_file:
            json.dump({"index": index, "metadata": metadata.model_dump()}, checkpoint_file)
    
    def load_checkpoint(self) -> tuple[int, Metadata] | None:
        checkpoint_path = os.path.join(self.checkpoints_path, self.law_code)

        if not os.path.exists(checkpoint_path):
            return None
        
        checkpoints = [f for f in os.listdir(checkpoint_path) if f.endswith(".json")]
        if not checkpoints:
            return None
        
        checkpoints.sort(key=lambda x: int(x.split(".")[0]))
        last_checkpoint = checkpoints[-1]
        checkpoint_file = os.path.join(checkpoint_path, last_checkpoint)
        
        with open(checkpoint_file, "r") as file:
            checkpoint = json.load(file)
            index = checkpoint["index"]
            metadata = Metadata.model_validate(checkpoint["metadata"], strict=False, from_attributes=True)

        return index, metadata

    def run(self):
        self.last_checkpoint = self.load_checkpoint()
        
        start_index = 0
        
        if self.last_checkpoint:
            start_index = self.last_checkpoint[0] + 1
            self.metadata = self.metadata[start_index:]
        
        for index, metadata in enumerate(self.metadata):
            console.print(f"Processing {metadata.file_path}...")
            
            try:
                upload_response = self.upload(metadata)
            except FileNotFoundError:
                console.print(f"File not found! Skipping {metadata.file_path}")
                continue
            
            console.print(f"File uploaded with ID: {upload_response.json()['id']}")
            
            console.print(f"Saving checkpoint for {metadata.file_path}...")
            self.save_checkpoint(start_index + index, metadata)
            console.print(f"Checkpoint saved at {self.checkpoints_path}...")

            console.print(f"Ingesting {metadata.file_path}...")
            ingest_response = self.ingest(upload_response.json()["id"], metadata)
            
            for content in ingest_response.iter_content(chunk_size=1024):
                try:
                    content = json.loads(content)
                    if content.get("status") == "success":
                        console.print(f"Ingested {metadata.file_path} successfully.")

                except json.JSONDecodeError:
                    console.print(content)
                    console.print(f"Error decoding JSON: {content}")
                    continue